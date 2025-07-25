def migrate(cr, version):
    # Map old bank codes to bank names
    bank_mapping = {
        'hbl': 'Habib Bank Limited',
        'ubl': 'United Bank Limited',
        'mcb': 'Muslim Commercial Bank',
        'abl': 'Allied Bank Limited',
        'nbl': 'National Bank of Pakistan',
        'scb': 'Standard Chartered Bank',
        'faysal': 'Faysal Bank',
        'js': 'JS Bank',
        'askari': 'Askari Bank',
        'soneri': 'Soneri Bank',
        'summit': 'Summit Bank',
        'silk': 'Silk Bank',
        'dubai': 'Dubai Islamic Bank',
        'meezan': 'Meezan Bank',
        'alfalah': 'Bank Alfalah',
        'habib_metro': 'Habib Metropolitan Bank',
        'first_women': 'First Women Bank',
        'punjab': 'Bank of Punjab',
        'khyber': 'Bank of Khyber',
        'sindh': 'Bank of Sindh',
        'industrial': 'Industrial Development Bank',
    }

    # Check if old column exists
    cr.execute("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'hr_payslip_run' AND column_name = 'bank_name_old'
    """)
    if not cr.fetchone():
        return

    # Migrate data from old column
    for old_code, bank_name in bank_mapping.items():
        # Find bank ID
        cr.execute("""
            SELECT id FROM res_bank 
            WHERE LOWER(name) LIKE %s
        """, ('%' + bank_name.lower() + '%',))
        bank_row = cr.fetchone()
        if bank_row:
            bank_id = bank_row[0]
            # Update records with this bank
            cr.execute("""
                UPDATE hr_payslip_run 
                SET bank_name = %s,
                    is_cash_payment = false
                WHERE bank_name_old = %s
            """, (bank_id, old_code))

    # Handle cash payments
    cr.execute("""
        UPDATE hr_payslip_run 
        SET is_cash_payment = true,
            bank_name = null
        WHERE bank_name_old = 'cash'
    """)

    # Drop old column
    cr.execute("""
        ALTER TABLE hr_payslip_run 
        DROP COLUMN IF EXISTS bank_name_old
    """) 