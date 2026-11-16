from odoo import models, fields, api


class IndentDemandByDestination(models.Model):
    _name = 'indent.demand.by.destination'
    _description = 'Indent Demand by Destination'

    dest_location_id = fields.Many2one('stock.location', string='Destination')
    line_ids = fields.One2many(
        'indent.destination.demand.line',
        'demand_id',
        string='Products'
    )

    total_demand_qty = fields.Float()
    issued_qty = fields.Float()
    pending_qty = fields.Float()
    uom_id = fields.Many2one('uom.uom')

    # 🔥 AUTO GENERATE ON OPEN
    @api.model
    def _generate_data(self):
        # clear old data
        self.search([]).unlink()

        demand_map = {}

        lines = self.env['indent.request.line'].search([
            ('indent_id.state', 'in', ['submitted', 'approved', 'done'])
        ])

        for line in lines:
            dest = line.indent_id.dest_location_id
            if not dest:
                continue

            demand_map.setdefault(dest.id, {})

            prod = line.product_id
            demand_map[dest.id].setdefault(prod.id, {
                'product_id': prod.id,
                'uom_id': prod.uom_id.id,
                'demand_qty': 0.0,
                'issued_qty': 0.0,
            })

            demand_map[dest.id][prod.id]['demand_qty'] += line.quantity
            demand_map[dest.id][prod.id]['issued_qty'] += line.issued_qty or 0.0

        for dest_id, products in demand_map.items():
            parent = self.create({
                'dest_location_id': dest_id,
            })

            total_demand = total_issued = 0.0

            for vals in products.values():
                self.env['indent.destination.demand.line'].create({
                    'demand_id': parent.id,
                    'product_id': vals['product_id'],
                    'uom_id': vals['uom_id'],
                    'demand_qty': vals['demand_qty'],
                    'issued_qty': vals['issued_qty'],
                })

                total_demand += vals['demand_qty']
                total_issued += vals['issued_qty']

            parent.total_demand_qty = total_demand
            parent.issued_qty = total_issued
            parent.pending_qty = total_demand - total_issued
    @api.model
    def action_open_demand_by_destination(self):
        # 🔥 auto-generate every time
        self._generate_data()

        return {
            'type': 'ir.actions.act_window',
            'name': 'Demand by Destination',
            'res_model': 'indent.demand.by.destination',
            'view_mode': 'list,form',
            'target': 'current',
        }