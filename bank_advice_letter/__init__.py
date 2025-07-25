from . import models

def bank_advice_post_init_hook(env):
    """Post-init hook to migrate bank data"""
    env['hr.payslip.run']._handle_bank_name_migration()