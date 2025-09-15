{
    "name": "FBR Integration Enhanced",
    "version": "18.0.1.0",
    "summary": "Enhanced FBR integration with dropdown support",
    "description": "Integrate Odoo invoices with FBR's real-time invoice reporting system with dropdown fields.",
    "category": "Accounting",
    "price": 400,
    "currency": "USD",
    "author": "Usama Asif",
    "website": "https://pearlsol.com/",
    "depends": ["base", "account", "product"],
    "data": [
        "security/ir.model.access.csv",
        "views/setting.xml",
        "views/sync_views.xml",
        "views/move.xml",
        "views/views.xml",
        "views/logs_view.xml",
        "reports/invoice_report.xml",
        "data/data.xml",  # Move data.xml to the end
    ],
    "installable": True,
    "application": True,
    "license": "LGPL-3"
    
}