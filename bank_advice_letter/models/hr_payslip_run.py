from odoo import models, fields, api
from odoo.exceptions import UserError
from num2words import num2words


class HrPayslipRunPaymentMethodLine(models.Model):
    _name = 'hr.payslip.run.payment.method.line'
    _description = 'Payslip Run Payment Method Line'

    payslip_run_id = fields.Many2one('hr.payslip.run', string='Payslip Run', ondelete='cascade')
    payment_type = fields.Selection(
        [('bank', 'Bank'), ('cash', 'Cash')],  # type: ignore
        string='Payment Type', required=True
    )
    bank_id = fields.Many2one('res.bank', string='Bank', domain="[]", help='Select the bank', ondelete='restrict')
    journal_id = fields.Many2one('account.journal', string='Journal', domain="[('type', 'in', ['bank', 'cash'])]", help='Select the journal')
    cheque_number = fields.Char(string='Cheque Number', compute='_compute_cheque_fields', store=False, readonly=True)
    cheque_date = fields.Date(string='Cheque Date', compute='_compute_cheque_fields', store=False, readonly=True)
    cheque_amount = fields.Float(string='Cheque Amount', compute='_compute_cheque_amount', store=True)
    check_book_id = fields.Many2one(
        'check.book', string='Check Book',
        domain="[('journal_id', '=', journal_id), ('status', '=', 'active')]"
    )
    check_book_page_id = fields.Many2one(
        'check.book.page', string='Check Book Page',
        domain="[('check_book_id', '=', check_book_id), ('status', '=', 'pending')]"
    )
    payment_id = fields.Many2one('account.payment', string='Payment', readonly=True)

    amount_in_words = fields.Char(
        string="Amount in Words",
        compute="_compute_amount_in_words"
    )

    @api.depends('cheque_amount')
    def _compute_amount_in_words(self):
        for rec in self:
            amount = rec.cheque_amount or 0
            rec.amount_in_words = num2words(amount, lang='en').title() + " Only" if amount else ""

    @api.depends('payslip_run_id', 'bank_id', 'payment_type', 'journal_id')
    def _compute_cheque_amount(self):
        for rec in self:
            payslip_run = rec.payslip_run_id
            if not payslip_run:
                rec.cheque_amount = 0.0
                continue
            journal = rec.journal_id
            if rec.payment_type == 'cash' and journal and journal.type == 'cash':
                # Only sum for employees whose bank account is set to the 'Cash' bank
                cash_bank = rec.env['res.bank'].search([('name', '=', 'Cash')], limit=1)
                rec.cheque_amount = sum(
                    slip.net_wage for slip in payslip_run.slip_ids
                    if slip.employee_id.bank_account_id and slip.employee_id.bank_account_id.bank_id == cash_bank
                )
            elif rec.payment_type == 'cash':
                rec.cheque_amount = sum(slip.net_wage for slip in payslip_run.slip_ids)
            elif rec.payment_type == 'bank' and rec.bank_id:
                rec.cheque_amount = sum(
                    slip.net_wage for slip in payslip_run.slip_ids
                    if slip.employee_id.bank_account_id and slip.employee_id.bank_account_id.bank_id == rec.bank_id
                )
            else:
                rec.cheque_amount = 0.0

    @api.depends('payment_id', 'payment_id.check_book_page_id', 'payment_id.cheque_date')
    def _compute_cheque_fields(self):
        for rec in self:
            if rec.payment_id and rec.payment_id.check_book_page_id:
                rec.cheque_number = rec.payment_id.check_book_page_id.name
                rec.cheque_date = rec.payment_id.cheque_date
            elif rec.payment_id:
                rec.cheque_number = False
                rec.cheque_date = rec.payment_id.cheque_date
            else:
                rec.cheque_number = False
                rec.cheque_date = False

    def action_create_payment(self):
        self.ensure_one()
        if self.payment_id:
            raise UserError("A payment has already been created for this journal. You cannot create it again.")
        payslip_run = self.payslip_run_id
        if not payslip_run:
            raise UserError('Payslip Run is not set.')
        journal = self.journal_id
        if not journal:
            raise UserError('Please select a journal.')
        # Fetch Payable A/C from SLR journal
        slr_journal = self.env['account.journal'].search([('code', '=', 'SLR')], limit=1)
        if not slr_journal or not slr_journal.payable_account_id:
            raise UserError('Please set the Payable A/C on the SLR (Salaries) journal before creating a payment.')
        # Prevent duplicate payments for the same payslip run, journal, and bank
        existing = self.search([
            ('id', '!=', self.id),
            ('payslip_run_id', '=', self.payslip_run_id.id),
            ('journal_id', '=', self.journal_id.id),
            ('bank_id', '=', self.bank_id.id),
            ('payment_id', '!=', False),
        ])
        if existing:
            raise UserError("A payment has already been created for this journal and bank in this payslip run. You cannot create it again.")
        # Get employees for this payment method
        if self.payment_type == 'cash' and journal.type == 'cash':
            slips = payslip_run.slip_ids.filtered(
                lambda slip: (
                    (slip.employee_id.bank_account_id and slip.employee_id.bank_account_id.acc_number and slip.employee_id.bank_account_id.acc_number.lower() == 'cash') or
                    any(cat.name.lower() == 'cash' for cat in slip.employee_id.category_ids)
                )
            )
        elif self.payment_type == 'cash':
            slips = payslip_run.slip_ids
        elif self.payment_type == 'bank' and self.bank_id:
            slips = payslip_run.slip_ids.filtered(
                lambda slip: slip.employee_id.bank_account_id and slip.employee_id.bank_account_id.bank_id == self.bank_id
            )
        else:
            raise UserError('Please select a bank for bank payment type.')
        if not slips:
            raise UserError('No payslips found for this payment method.')
        total_amount = sum(slip.net_wage for slip in slips)
        if total_amount <= 0:
            raise UserError('Total amount must be greater than 0.')
        if total_amount > sum(slip.net_wage for slip in slips):
            raise UserError('Total payment cannot exceed total payslip amount.')
        # Prepare payment values
        payment_vals = {
            'payment_type': 'outbound',
            'partner_type': 'supplier',
            'journal_id': journal.id,
            'amount': total_amount,
            'currency_id': payslip_run.slip_ids[0].company_id.currency_id.id if payslip_run.slip_ids else journal.company_id.currency_id.id,
            'date': fields.Date.today(),
            'memo': f"Payroll Payment - {payslip_run.name} - {self.bank_id.name if self.bank_id else 'Cash'}",
        }
        # Set payment method
        if hasattr(journal, 'outbound_payment_method_line_ids'):
            outbound_payment_methods = journal.outbound_payment_method_line_ids
            if outbound_payment_methods:
                payment_vals['payment_method_line_id'] = outbound_payment_methods[0].id
            else:
                raise UserError('No outbound payment methods available for the selected journal.')
        else:
            payment_vals['payment_method_id'] = self.env.ref('account.account_payment_method_manual_out').id
        # Create the payment (keep in draft, do not post)
        payment = self.env['account.payment'].create(payment_vals)
        # Get or create the account move
        account_move = payment.move_id
        if not account_move:
            move_vals = {
                'journal_id': journal.id,
                'date': fields.Date.today(),
                'ref': f"Payroll Payment - {payslip_run.name}",
                'move_type': 'entry',
                'currency_id': journal.currency_id.id or journal.company_id.currency_id.id,
            }
            account_move = self.env['account.move'].create(move_vals)
            payment.write({'move_id': account_move.id})
        # Remove any existing move lines
        if account_move.line_ids:
            if account_move.state == 'posted':
                account_move.button_draft()
            account_move.line_ids.unlink()
        # Create per-employee move lines (with batch mode logic)
        batch_mode = self.env.company.batch_payroll_move_lines if hasattr(self.env.company, 'batch_payroll_move_lines') else False
        move_line_vals = []
        for slip in slips:
            employee = slip.employee_id
            amount = slip.net_wage
            debit_account = slr_journal.payable_account_id.id
            credit_account = journal.default_credit_account_id.id if hasattr(journal, 'default_credit_account_id') and journal.default_credit_account_id else journal.default_account_id.id
            partner = False if batch_mode else (employee.work_contact_id.id if employee.work_contact_id else False)
            # Debit line (employee/expense)
            debit_line = {
                'move_id': account_move.id,
                'account_id': debit_account,
                'partner_id': partner,
                'name': f"{employee.name} - Payroll Payment - {payslip_run.name}",
                'debit': amount,
                'credit': 0.0,
            }
            # Credit line (bank/treasury)
            credit_line = {
                'move_id': account_move.id,
                'account_id': credit_account,
                'partner_id': partner,
                'name': f"{employee.name} - Payroll Payment - {payslip_run.name}",
                'debit': 0.0,
                'credit': amount,
            }
            move_line_vals.extend([debit_line, credit_line])
        self.env['account.move.line'].create(move_line_vals)
        # Do NOT post the move or payment automatically; keep in draft
        self.payment_id = payment
        # Auto-fetch cheque number and date after payment creation
        vals = {}
        if hasattr(payment, 'check_book_page_id') and payment.check_book_page_id:
            vals['cheque_number'] = payment.check_book_page_id.name
            vals['cheque_date'] = payment.cheque_date
        elif hasattr(payment, 'cheque_number') and payment.cheque_number:
            vals['cheque_number'] = payment.cheque_number
            vals['cheque_date'] = payment.cheque_date
        if vals:
            self.write(vals)
        self.message_post_on_payment(payment, total_amount, slips)
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'account.payment',
            'view_mode': 'form',
            'res_id': payment.id,
            'target': 'current',
        }

    def message_post_on_payment(self, payment, total_amount, slips):
        # Post a message on the payslip run for traceability
        payslip_run = self.payslip_run_id
        if payslip_run:
            payslip_run.message_post(  # type: ignore
                body=f"Payment created: <a href='/web#id={payment.id}&model=account.payment'>{payment.name}</a> for {len(slips)} employees. Total: {total_amount}",  # type: ignore
                message_type='notification'
            )

    def action_print_advice_letter(self):
        self.ensure_one()
        if self.payment_type == 'cash' or (self.journal_id and self.journal_id.type == 'cash'):
            raise UserError('No letter for cash payments.')
        # Pass self to the report so 'doc' is available in the template
        return self.env.ref('bank_advice_letter.action_report_payroll_letter').report_action(self)

    def get_slips(self):
        payslip_run = self.payslip_run_id
        journal = self.journal_id
        if self.payment_type == 'cash' and journal and journal.type == 'cash':
            return payslip_run.slip_ids.filtered(
                lambda slip: (
                    (slip.employee_id.bank_account_id and slip.employee_id.bank_account_id.acc_number and slip.employee_id.bank_account_id.acc_number.lower() == 'cash') or
                    any(cat.name.lower() == 'cash' for cat in slip.employee_id.category_ids)
                )
            )
        elif self.payment_type == 'cash':
            return payslip_run.slip_ids
        elif self.payment_type == 'bank' and self.bank_id:
            return payslip_run.slip_ids.filtered(
                lambda slip: slip.employee_id.bank_account_id and slip.employee_id.bank_account_id.bank_id == self.bank_id
            )
        return self.env['hr.payslip']

    def action_view_payment(self):
        self.ensure_one()
        if not self.payment_id:
            raise UserError("No payment has been created yet.")
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'account.payment',
            'view_mode': 'form',
            'res_id': self.payment_id.id,
            'target': 'current',
        }

    @api.onchange('bank_id')
    def _onchange_bank_id(self):
        if self.bank_id and not self.journal_id:
            # Find the first bank journal linked to this bank
            journal = self.env['account.journal'].search([
                ('bank_id', '=', self.bank_id.id),
                ('type', 'in', ['bank', 'cash'])
            ], limit=1)
            if journal:
                self.journal_id = journal

    @api.onchange('journal_id')
    def _onchange_journal_id(self):
        if self.journal_id and not self.bank_id:
            # If the journal has a bank_id, set it
            if self.journal_id.bank_id:
                self.bank_id = self.journal_id.bank_id


# Extend HrPayslipRun to add One2many
class HrPayslipRun(models.Model):
    _inherit = 'hr.payslip.run'

    payment_method_line_ids = fields.One2many(
        'hr.payslip.run.payment.method.line',
        'payslip_run_id',
        string='Payment Methods'
    )

    # Only keep the new Many2one field
    bank_name = fields.Many2one(
        'res.bank',
        string='Bank Name',
        help='Select the bank for this payroll batch',
        ondelete='restrict'
    )
    
    is_cash_payment = fields.Boolean(
        string='Is Cash Payment',
        help='Check if this is a cash payment'
    )
    
    cheque_number = fields.Char(
        string='Cheque Number',
        help='Enter the cheque number for bank advice'
    )
    
    cheque_date = fields.Date(
        string='Cheque Date',
        help='Date of the cheque'
    )
    
    cheque_amount = fields.Float(
        string='Cheque Amount',
        help='Total amount of the cheque',
        compute='_compute_cheque_amount',
        store=True
    )

    amount_in_words = fields.Char(
        string="Amount in Words",
        compute="_compute_amount_in_words"
    )

    @api.depends('slip_ids.net_wage', 'bank_name', 'is_cash_payment')
    def _compute_cheque_amount(self):
        for record in self:
            if (record.bank_name or record.is_cash_payment) and record.slip_ids:
                if record.is_cash_payment:
                    record.cheque_amount = sum(slip.net_wage for slip in record.slip_ids)
                else:
                    total = sum(
                        slip.net_wage for slip in record.slip_ids
                        if slip.employee_id.bank_account_id and \
                           slip.employee_id.bank_account_id.bank_id == record.bank_name
                    )
                    record.cheque_amount = total
            else:
                record.cheque_amount = 0.0

    def _compute_amount_in_words(self):
        for rec in self:
            amount = rec.cheque_amount or 0
            rec.amount_in_words = num2words(amount, lang='en').title() + " Only" if amount else ""

    def action_print_advice_letter(self):
        """Print the bank advice letter"""
        if self.is_cash_payment:
            raise UserError("No letter for cash payments.")
        if not self.bank_name:
            raise UserError("Please select a bank before printing the advice letter.")
        if not self.cheque_number:
            raise UserError("Please enter the cheque number before printing the advice letter.")
        return self.env.ref('bank_advice_letter.action_report_payroll_letter').report_action(self)  # type: ignore

    def get_employees_by_bank(self, bank_name):
        """Get employees filtered by bank (using only primary bank account)"""
        if not bank_name or not self.slip_ids:  # type: ignore
            return []
        if self.is_cash_payment:
            return self.slip_ids.sorted(key=lambda r: r.employee_id.name)  # type: ignore
        filtered_slips = self.slip_ids.filtered(
            lambda slip: slip.employee_id.bank_account_id and \
                slip.employee_id.bank_account_id.bank_id == bank_name
        )  # type: ignore
        return filtered_slips.sorted(key=lambda r: r.employee_id.name)  # type: ignore

    @api.onchange('bank_name', 'slip_ids')
    def _onchange_bank_name(self):
        """Update domain for bank_name field based on available primary bank accounts only"""
        if not self.slip_ids:
            return {'domain': {'bank_name': []}}
        bank_ids = list(set(
            slip.employee_id.bank_account_id.bank_id.id
            for slip in self.slip_ids
            if slip.employee_id.bank_account_id and slip.employee_id.bank_account_id.bank_id
        ))
        return {'domain': {'bank_name': [('id', 'in', bank_ids)]}}

    def _handle_bank_name_migration(self):
        """Migration logic for bank name, currently does nothing."""
        pass