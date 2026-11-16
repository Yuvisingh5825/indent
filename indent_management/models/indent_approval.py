from odoo import models, fields

class IndentApproval(models.Model):
    _name = 'indent.approval'
    _description = 'Indent Approval'

    indent_id = fields.Many2one('indent.request', ondelete='cascade')
    approver_id = fields.Many2one('res.users')
    level = fields.Integer()
    status = fields.Selection([
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected')
    ], default='pending')
    approval_date = fields.Datetime()
