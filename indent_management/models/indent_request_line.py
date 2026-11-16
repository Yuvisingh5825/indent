from odoo import models, fields, api


class IndentRequestLine(models.Model):
    _name = 'indent.request.line'
    _description = 'Indent Request Line'

    indent_id = fields.Many2one('indent.request', ondelete='cascade')

    product_id = fields.Many2one('product.product', required=True)
    description = fields.Char()
    quantity = fields.Float(default=1)

    uom_id = fields.Many2one(
        'uom.uom', related='product_id.uom_id', store=True
    )

    vendor_ids = fields.Many2many(
        "res.partner",
        string="Vendors",
        domain="[('supplier_rank','>',0)]"
    )

    request_date = fields.Date(
        related='indent_id.request_date',
        store=True,
        string='Request Date'
    )

    # used by the demand-by-destination reports
    issued_qty = fields.Float(string="Issued Qty", readonly=True)

    @api.onchange('product_id')
    def _onchange_product(self):
        """Vendors come from the product's Purchase tab (supplier list).
        If the product has none, the list stays empty and the user adds
        vendors on the line itself."""
        if not self.product_id:
            self.vendor_ids = [(5, 0, 0)]
            return
        sellers = self.product_id.seller_ids.mapped('partner_id')
        self.vendor_ids = [(6, 0, sellers.ids)]
