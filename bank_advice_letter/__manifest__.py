# Copyright © 2022 Pearl Solutions (https://pearlsol.com)
# License OPL-1 (https://www.odoo.com/documentation/18.0/legal/licenses.html).
{
    'name': 'Bank Advice Letter',
    'version': '18.0.1.0.0',
    'category': 'Human Resources/Payroll',
    'summary': 'Generate bank advice letters for payroll processing',
    'description': """
This module extends the HR Payroll functionality to generate
bank advice letters for salary payments.

Key Features:
-------------
- Generate advice letters grouped by journal (bank or cash)
- Bank selection for payroll batches
- Employee bank account management
- Formatted printable reports (advice letter)
- Cheque details tracking
- Journal-specific payment creation

Configuration:
--------------
Make sure to configure the **Payable Account** in:
Accounting > Settings > Journals > Salaries (SLR)
""",
    'author': 'Pearl Solutions',
    'website': 'https://pearlsol.com/',
    'license': 'OPL-1',
    'support': 'info@pearlsol.com',
    'price': 178.0,
    'currency': 'USD',
    'depends': ['base', 'hr_payroll', 'hr', 'web'],
    'data': [
        'security/ir.model.access.csv',
        'data/report_paperformat.xml',
        'data/actions.xml',
        'reports/base_payslip_report.xml',
        'reports/monthly_payslip.xml',
        'reports/monthly_payslip_report.xml',
        'reports/payroll_advice_letter_report.xml',
        'views/hr_payslip_views.xml',
        'views/hr_payslip_run_views.xml',
        'views/hr_employee_bank_views.xml',
        'views/account_journal_view.xml',
        'views/hr_payslip_run_payment_method_line_views.xml',
        'views/hr_payslip_run_payment_method_line_view.xml',
    ],
    'images': [
        'static/description/icon.png',
        'static/description/Cheque.png',
        'static/description/Grid.png',
        'static/description/Journal.png',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
    'post_init_hook': 'bank_advice_post_init_hook',
}
