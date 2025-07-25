# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError

class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    def action_print_monthly_payslip(self):
        """
        Action method to print monthly payslip report
        This method is called when the 'Print Monthly Payslip' button is clicked
        """
        # Ensure we have payslips to print
        if not self:
            raise UserError(_('No payslip selected for printing.'))
        
        # Get the report action
        return self.env.ref('bank_advice_letter.action_monthly_payslip_report').report_action(self)

    @api.model
    def get_payslips_for_period(self, date_from, date_to, employee_ids=None, department_ids=None):
        """
        Helper method to get payslips for a specific period
        Can be used for batch printing of multiple payslips
        """
        domain = [
            ('date_from', '>=', date_from),
            ('date_to', '<=', date_to),
            ('state', 'in', ['done', 'paid'])
        ]
        
        if employee_ids:
            domain.append(('employee_id', 'in', employee_ids))
        
        if department_ids:
            domain.append(('employee_id.department_id', 'in', department_ids))
        
        return self.search(domain)

class HrEmployee(models.Model):
    _inherit = 'hr.employee'
    
    # Add father_name field if it doesn't exist
    father_name = fields.Char(string="Father's Name", help="Employee's father name")
    employee_number = fields.Char(string="Employee Number", help="Employee identification number")
    
    @api.model
    def _get_employee_display_name(self):
        """
        Method to format employee display name for reports
        """
        return self.name or 'Unknown Employee'

class HrPayslipRun(models.Model):
    _inherit = 'hr.payslip.run'
    
    def action_print_all_monthly_payslips(self):
        """
        Action to print all payslips in this payslip run/batch
        """
        if not self.slip_ids:
            raise UserError(_('No payslips found in this batch.'))
        
        # Filter only confirmed payslips
        confirmed_payslips = self.slip_ids.filtered(lambda p: p.state in ['done', 'paid'])
        
        if not confirmed_payslips:
            raise UserError(_('No confirmed payslips found in this batch.'))
        
        return self.env.ref('bank_advice_letter.action_monthly_payslip_report').report_action(confirmed_payslips)