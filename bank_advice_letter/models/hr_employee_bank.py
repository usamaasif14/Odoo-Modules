from odoo import models, fields, api


class HrEmployeeBank(models.Model):
    _name = 'hr.employee.bank'
    _description = 'Employee Bank Information'
    _rec_name = 'employee_id'

    employee_id = fields.Many2one(
        'hr.employee',
        string='Employee',
        required=True,
        ondelete='cascade'
    )
    
    bank_name = fields.Selection([
        ('hbl', 'Habib Bank Limited (HBL)'),
        ('ubl', 'United Bank Limited (UBL)'),
        ('mcb', 'Muslim Commercial Bank (MCB)'),
        ('abl', 'Allied Bank Limited (ABL)'),
        ('nbl', 'National Bank of Pakistan (NBP)'),
        ('scb', 'Standard Chartered Bank'),
        ('faysal', 'Faysal Bank'),
        ('js', 'JS Bank'),
        ('askari', 'Askari Bank'),
        ('soneri', 'Soneri Bank'),
        ('summit', 'Summit Bank'),
        ('silk', 'Silk Bank'),
        ('dubai', 'Dubai Islamic Bank'),
        ('meezan', 'Meezan Bank'),
        ('alfalah', 'Bank Alfalah'),
        ('habib_metro', 'Habib Metropolitan Bank'),
        ('first_women', 'First Women Bank'),
        ('punjab', 'Bank of Punjab'),
        ('khyber', 'Bank of Khyber'),
        ('sindh', 'Bank of Sindh'),
        ('industrial', 'Industrial Development Bank'),
        ('cash', 'Cash Payment'),
    ], string='Bank Name', required=True)
    
    account_number = fields.Char(
        string='Account Number',
        help='Employee bank account number'
    )
    
    is_primary = fields.Boolean(
        string='Primary Account',
        default=True,
        help='Primary bank account for salary'
    )
    
    active = fields.Boolean(default=True)

    @api.model
    def create(self, vals):
        # Ensure only one primary account per employee
        if vals.get('is_primary') and vals.get('employee_id'):
            existing_primary = self.search([
                ('employee_id', '=', vals['employee_id']),
                ('is_primary', '=', True)
            ])
            existing_primary.write({'is_primary': False})
        return super().create(vals)

    def write(self, vals):
        if vals.get('is_primary'):
            for record in self:
                # Remove primary flag from other accounts of same employee
                other_accounts = self.search([
                    ('employee_id', '=', record.employee_id.id),
                    ('id', '!=', record.id)
                ])
                other_accounts.write({'is_primary': False})
        return super().write(vals)


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    bank_ids = fields.One2many(
        'hr.employee.bank',
        'employee_id',
        string='Bank Accounts'
    )
    
    primary_bank_id = fields.Many2one(
        'hr.employee.bank',
        string='Primary Bank',
        compute='_compute_primary_bank',
        store=True
    )

    @api.depends('bank_ids.is_primary')
    def _compute_primary_bank(self):
        for employee in self:
            primary_bank = employee.bank_ids.filtered('is_primary')
            employee.primary_bank_id = primary_bank[0] if primary_bank else False