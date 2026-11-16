from odoo import api, fields, models
from odoo.exceptions import UserError


class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

    # shown on the Compare screen (read from the RFQ of this line)
    indent_is_lowest = fields.Boolean(
        string="Lowest", related="order_id.is_lowest_price"
    )
    indent_is_selected = fields.Boolean(
        string="Selected", related="order_id.is_selected_rfq"
    )
    indent_vendor_total = fields.Monetary(
        string="Vendor Total",
        related="order_id.amount_untaxed",
        currency_field="currency_id",
    )

    def action_indent_send_rfq(self):
        self.ensure_one()
        return self.order_id.action_indent_send_rfq()

    def action_select_vendor(self):
        self.ensure_one()
        return self.order_id.action_select_vendor()
    indent_vendor_total = fields.Monetary(
        string="Vendor Total",
        related="order_id.amount_untaxed",
        currency_field="currency_id",
    )

    def action_indent_send_rfq(self):
        self.ensure_one()
        return self.order_id.action_indent_send_rfq()

    def action_select_vendor(self):
        self.ensure_one()
        return self.order_id.action_select_vendor()


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    indent_request_id = fields.Many2one(
        "indent.request", string="Indent", copy=False, index=True, readonly=True
    )
    is_selected_rfq = fields.Boolean(string="Selected", copy=False, readonly=True)
    is_lowest_price = fields.Boolean(
        string="Lowest Price", compute="_compute_is_lowest_price"
    )

    @api.depends(
        "amount_untaxed",
        "state",
        "indent_request_id.po_ids.amount_untaxed",
        "indent_request_id.po_ids.state",
    )
    def _compute_is_lowest_price(self):
        """The RFQ with the lowest total (among live RFQs of the same indent
        that already have a price) is flagged. It is only a hint."""
        for rec in self:
            rec.is_lowest_price = False

        for indent in self.mapped("indent_request_id"):
            pos = indent.po_ids.filtered(
                lambda p: p.state != "cancel" and p.amount_untaxed > 0
            )
            if not pos:
                continue
            lowest = min(pos.mapped("amount_untaxed"))
            for rec in self.filtered(lambda r: r.indent_request_id == indent):
                rec.is_lowest_price = (
                    rec.state != "cancel"
                    and rec.amount_untaxed > 0
                    and rec.amount_untaxed == lowest
                )

    @api.depends("partner_id")
    def _compute_display_name(self):
        """On the Compare screen the group title must be the vendor, not the RFQ number."""
        super()._compute_display_name()
        if self.env.context.get("indent_compare"):
            for rec in self:
                if rec.partner_id:
                    rec.display_name = "%s (%s)" % (rec.partner_id.display_name, rec.name)

    # ------------------------------------------------------------
    def action_indent_send_rfq(self):
        """Open the email wizard with the price-free RFQ template."""
        self.ensure_one()
        if self.state not in ("draft", "sent"):
            raise UserError("Only a draft / sent RFQ can be sent.")
        template = self.env.ref("indent_management.mail_template_indent_rfq")
        ctx = dict(
            self.env.context,
            default_model="purchase.order",
            default_res_ids=self.ids,
            default_template_id=template.id,
            default_composition_mode="comment",
            mark_rfq_as_sent=True,
            force_email=True,
        )
        return {
            "type": "ir.actions.act_window",
            "res_model": "mail.compose.message",
            "view_mode": "form",
            "views": [(False, "form")],
            "target": "new",
            "context": ctx,
        }

    def action_select_vendor(self):
        """Choose this vendor: confirm this RFQ (-> Purchase Order) and
        cancel all other RFQs of the indent."""
        self.ensure_one()
        indent = self.indent_request_id

        if not indent:
            raise UserError("This RFQ is not linked to any Indent.")
        if indent.state != "rfq":
            raise UserError("The indent is not in 'RFQ Created' state.")
        if indent.selected_po_id:
            raise UserError(
                "A vendor is already selected for this indent: %s"
                % indent.selected_po_id.partner_id.display_name
            )
        if self.state not in ("draft", "sent"):
            raise UserError("Only a draft / sent RFQ can be selected.")
        if self.amount_untaxed <= 0:
            raise UserError("Please enter the vendor's price before selecting it.")

        others = indent.po_ids.filtered(
            lambda p: p.id != self.id and p.state in ("draft", "sent", "to approve")
        )
        others.button_cancel()

        self.is_selected_rfq = True
        indent.selected_po_id = self.id
        self.button_confirm()

        indent.message_post(
            body="Vendor <b>%s</b> selected (%s). Total: %s. Other RFQs were cancelled."
            % (self.partner_id.display_name, self.name, self.amount_untaxed)
        )
        return indent.action_compare_rfqs()
