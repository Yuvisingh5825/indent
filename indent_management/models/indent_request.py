from odoo import models, fields, api
from odoo.exceptions import UserError


class IndentRequest(models.Model):
    _name = "indent.request"
    _description = "Indent Request"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    # ---------------- BASIC ----------------
    name = fields.Char(default="New", copy=False, tracking=True)
    request_date = fields.Date(default=fields.Date.today)

    requester_id = fields.Many2one(
        "res.users", default=lambda self: self.env.user, readonly=True
    )

    is_dropship = fields.Boolean(string="Dropship", tracking=True)

    rejection_reason = fields.Text(
        string="Rejection Reason", readonly=True, tracking=True, default="Rejection Reason"
    )

    rejected_by_id = fields.Many2one(
        "res.users",
        string="Rejected By",
        tracking=True,
        readonly=True,
    )

    reset_by_id = fields.Many2one(
    "res.users",
    string="Reset By",
    readonly=True,
    tracking=True,
)


    active = fields.Boolean(default=True)
    priority = fields.Selection(
        [
            ("0", "Low"),
            ("1", "Normal"),
            ("2", "High"),
            ("3", "Urgent"),
        ],
        default="1",
        tracking=True,
    )

    project_id = fields.Many2one("account.analytic.account")
    department_id = fields.Many2one(
        "hr.department",
        string="Department",
        related="requester_id.employee_id.department_id",
        store=True,
        readonly=True,
    )

    # 🔥 FINAL DESTINATION
    dest_location_id = fields.Many2one(
        "stock.location",
        string="Final Destination",
        domain="[('usage','=','internal')]",
        readonly=True,
    )

    line_ids = fields.One2many("indent.request.line", "indent_id", string="Items")

    # ---------------- LINKS ----------------
    po_ids = fields.Many2many("purchase.order", string="Purchase Orders")
    selected_po_id = fields.Many2one(
        "purchase.order", string="Selected RFQ", readonly=True, copy=False
    )

    # ---------------- COUNTS ----------------
    po_count = fields.Integer(compute="_compute_counts")

    # ---------------- STATE ----------------
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("submitted", "Waiting Approval"),
            ("approved", "Approved"),
            ("rfq", "RFQ Created"),
            ("partial", "Partially Issued"),
            ("done", "Done"),
            ("rejected", "Rejected"),
            ("cancelled", "Cancelled"),
        ],
        default="draft",
        tracking=True,
    )

    # ---------------- RECEIPT NO ----------------

    # ---------------- ADMIN CHECK ----------------
    def _check_approver(self):
        user = self.env.user

        # Admin always allowed
        if user.has_group("base.group_system"):
            return

        for rec in self:
            # Self approval not allowed
            if rec.requester_id.id == user.id:
                raise UserError("You cannot approve your own indent.")

            dept = rec.department_id
            if not dept or not dept.manager_id:
                raise UserError("Department Manager not defined.")

            manager_user = dept.manager_id.user_id
            if not manager_user:
                raise UserError("Department Manager has no linked user.")

            if manager_user.id != user.id:
                raise UserError(
                    "Only Department Manager or Administrator can approve this indent."
                )

    # ---------------- COMPUTES ----------------
    def _compute_counts(self):
        for rec in self:
            rec.po_count = len(rec.po_ids)

    # ---------------- SUBMIT ----------------
    def action_submit(self):
        for rec in self:
            if not rec.line_ids:
                raise UserError("Add at least one item.")
            rec.state = "submitted"

    # ---------------- APPROVAL ----------------
    def action_approve(self):
        self._check_approver()
        self.state = "approved"

    # ---------------- REJECT (ADMIN ONLY) ----------------
    def action_open_reject_wizard(self):
        self._check_approver()
        self.ensure_one()

        return {
            "type": "ir.actions.act_window",
            "name": "Reject Indent",
            "res_model": "indent.reject.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_indent_id": self.id},
        }

    def action_reset_to_draft(self):
        for rec in self:
            if rec.state not in ("rejected", "cancelled"):
                continue
            rec.write(
                {
                    "state": "draft",
                    "reset_by_id": self.env.user.id,
                    # old (cancelled) RFQs stay in the system, but are detached so
                    # that a fresh Create RFQ starts a clean comparison.
                    "po_ids": [(5, 0, 0)],
                    "selected_po_id": False,
                }
            )
            rec.message_post(body="Indent reset to Draft.")

    # ---------------- CREATE RFQ (ONE PER VENDOR) ----------------
    def action_create_po(self):
        self.ensure_one()

        if self.state != "approved":
            raise UserError("Indent must be approved.")
        if self.po_ids:
            raise UserError("RFQs have already been created for this Indent.")

        vendor_map = {}
        for line in self.line_ids:
            if not line.vendor_ids:
                raise UserError(
                    "Please select at least one vendor for %s"
                    % line.product_id.display_name
                )
            for vendor in line.vendor_ids:
                vendor_map.setdefault(vendor, []).append(line)

        if not vendor_map:
            raise UserError("Add at least one item with a vendor.")

        for vendor, lines in vendor_map.items():
            self._create_rfq_for_vendor(vendor, lines)

        self.state = "rfq"
        return self.action_compare_rfqs()

    def _create_rfq_for_vendor(self, vendor, lines):
        """One RFQ for one vendor. Price is filled by Odoo from the product's
        supplier info if present, otherwise 0: it is entered on the Compare screen."""
        self.ensure_one()

        po = self.env["purchase.order"].create(
            {
                "partner_id": vendor.id,
                "origin": self.name,
                "indent_request_id": self.id,
            }
        )
        pol = self.env["purchase.order.line"]
        uom_field = "product_uom_id" if "product_uom_id" in pol._fields else "product_uom"

        for line in lines:
            vals = {
                "order_id": po.id,
                "product_id": line.product_id.id,
                "product_qty": line.quantity,
                "name": line.description or line.product_id.display_name,
            }
            if line.uom_id:
                vals[uom_field] = line.uom_id.id
            pol.create(vals)

        self.po_ids = [(4, po.id)]
        return po

    # ---------------- COMPARE RFQs ----------------
    def action_compare_rfqs(self):
        self.ensure_one()
        action = self.env["ir.actions.act_window"]._for_xml_id(
            "indent_management.action_indent_rfq_comparison"
        )
        action["name"] = "RFQ Comparison - %s" % self.name
        action["domain"] = [("order_id", "in", self.po_ids.ids)]
        action["context"] = {}
        return action

    # ---------------- CANCEL ----------------
    def action_cancel(self):
        self._check_approver()
        for rec in self:
            if rec.selected_po_id:
                raise UserError(
                    "A vendor is already selected (%s). The indent can no longer be cancelled."
                    % rec.selected_po_id.partner_id.display_name
                )
            open_pos = rec.po_ids.filtered(
                lambda p: p.state in ("draft", "sent", "to approve")
            )
            open_pos.button_cancel()
            rec.state = "cancelled"
            rec.message_post(body="Indent cancelled. All its RFQs were cancelled.")

    # ---------------- SMART BUTTON ACTIONS ----------------
    def action_view_pos(self):
        return {
            "type": "ir.actions.act_window",
            "name": "Purchase Orders",
            "res_model": "purchase.order",
            "domain": [("id", "in", self.po_ids.ids)],
            "view_mode": "list,form",
        }

    # ---------------- DEFAULTS ----------------
    def _get_default_dest_location(self):
        warehouse = self.env["stock.warehouse"].search(
            [("company_id", "=", self.env.company.id)], limit=1
        )
        return warehouse.lot_stock_id.id if warehouse else False

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        if "dest_location_id" in fields_list and not res.get("dest_location_id"):
            res["dest_location_id"] = self._get_default_dest_location()
        return res

    # ---------------- SEQUENCE ----------------
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("dest_location_id"):
                vals["dest_location_id"] = self._get_default_dest_location()

            if vals.get("name", "New") == "New":
                vals["name"] = self.env["ir.sequence"].next_by_code("indent.request")

        return super().create(vals_list)
