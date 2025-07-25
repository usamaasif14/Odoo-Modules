# Copyright © 2025 Pearl Solutions (https://pearlsol.com)
# License OPL-1 (https://www.odoo.com/documentation/18.0/legal/licenses.html).

{
    'name': 'Bank Advice Letter',
    'version': '18.0.1.0.0',
    'category': 'Human Resources/Payroll',
    'summary': 'Generate bank advice letters for payroll processing',
    'description': """
<h2>Bank Advice Letter for Payroll</h2>
<p>This module extends the HR Payroll functionality to generate bank advice letters for salary payments.</p>

<h3>Key Features:</h3>
<ul>
  <li>Generate advice letters grouped by journal (bank or cash)</li>
  <li>Bank selection for payroll batches</li>
  <li>Employee bank account management</li>
  <li>Formatted printable reports (advice letter)</li>
  <li>Cheque details tracking</li>
  <li>Journal-specific payment creation</li>
</ul>

<h3>Configuration:</h3>
<p>Make sure to configure the <strong>Payable Account</strong> in:</p>
<p><em>Accounting &gt; Settings &gt; Journals &gt; Salaries (SLR)</em></p>
""",
    'author': 'Usama Asif',
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
