from odoo import models, fields
from odoo.exceptions import UserError


class IndentRejectWizard(models.TransientModel):
    _name = "indent.reject.wizard"
    _description = "Indent Rejection Reason"

    indent_id = fields.Many2one("indent.request", required=True)
    reason = fields.Text(string="Reason for Rejection", required=True)

    def action_confirm_reject(self):
        self.ensure_one()

        indent = self.indent_id
        indent.write(
            {
                "state": "rejected",
                "rejection_reason": self.reason,
                "rejected_by_id": self.env.user.id,
            }
        )

        # chatter message for rejection
        indent.write(
            {
                "state": "rejected",
                "rejection_reason": self.reason,
                "rejected_by_id": self.env.user.id,
            }
        )
