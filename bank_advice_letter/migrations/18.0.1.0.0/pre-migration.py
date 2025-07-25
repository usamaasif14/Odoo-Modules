def migrate(cr, version):
    # Rename the old bank_name column to prevent conflicts
    if column_exists(cr, 'hr_payslip_run', 'bank_name'):
        cr.execute("""
            ALTER TABLE hr_payslip_run 
            RENAME COLUMN bank_name TO bank_name_old
        """)

def column_exists(cr, table, column):
    cr.execute("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = %s AND column_name = %s
    """, (table, column))
    return bool(cr.fetchone()) 