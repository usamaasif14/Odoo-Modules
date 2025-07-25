from odoo import models, fields, api
from odoo.exceptions import ValidationError

class AccountJournal(models.Model):
    _inherit = 'account.journal'

    payable_account_id = fields.Many2one(
        'account.account',
        string='Payable A/C',
        domain=[('deprecated', '=', False)],
        help='Account to use for payroll payable (debit line in payroll payments)'
    )

    is_salary_journal = fields.Boolean(
        compute='_compute_is_salary_journal',
        store=False
    )

    def _compute_is_salary_journal(self):
        for rec in self:
            rec.is_salary_journal = (rec.code == 'SLR')

    @api.constrains('code', 'payable_account_id')
    def _check_payable_account_id_for_slr(self):
        for rec in self:
            code = (rec.code or '').strip().upper()
            if code == 'SLR' and not rec.payable_account_id:
                raise ValidationError("Payable A/C is required for Salaries (SLR) journals.") 