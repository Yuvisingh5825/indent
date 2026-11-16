from odoo import models, fields, api


class IndentDestinationDemandLine(models.Model):
    _name = 'indent.destination.demand.line'
    _description = 'Indent Destination Demand Line'

    demand_id = fields.Many2one(
        'indent.demand.by.destination',
        string='Demand',
        ondelete='cascade'
    )

    product_id = fields.Many2one(
        'product.product',
        string='Product'
    )

    uom_id = fields.Many2one(
        'uom.uom',
        string='UoM',
        related='product_id.uom_id',
        store=True
    )

    demand_qty = fields.Float(
        string='Demand Qty'
    )

    issued_qty = fields.Float(
        string='Issued Qty'
    )

    pending_qty = fields.Float(
        string='Pending Qty',
        compute='_compute_pending',
        store=True
    )

    @api.depends('demand_qty', 'issued_qty')
    def _compute_pending(self):
        for rec in self:
            rec.pending_qty = rec.demand_qty - rec.issued_qty
