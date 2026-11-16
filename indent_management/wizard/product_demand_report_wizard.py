from odoo import models, fields
from odoo.exceptions import UserError

class ProductDemandWizard(models.TransientModel):
    _name = 'product.demand.wizard'
    _description = 'Product Demand Wizard'

    date_from = fields.Date(required=True)
    date_to = fields.Date(required=True)

    def action_generate_report(self):
        if self.date_from > self.date_to:
            raise UserError("From Date must be before To Date")

        return {
            'type': 'ir.actions.act_window',
            'name': 'Product Demand (Month-wise)',
            'res_model': 'indent.request.line',
            'view_mode': 'list',
            'domain': [
                ('request_date', '>=', self.date_from),
                ('request_date', '<=', self.date_to),
            ],
            'context': {
                # 🔥 Dynamic grouping (THIS MAKES IT MONTH-WISE)
                'group_by': ['product_id', 'request_date:month'],
            }
        }
