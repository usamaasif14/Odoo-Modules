from odoo import fields, models, api, _


class ResCompany(models.Model):
    _inherit = 'res.company'

    strn_or_ntn = fields.Char(string="STRN")
    vat = fields.Char(related='partner_id.vat', string="NTN", readonly=False)


class ResPartner(models.Model):
    _inherit = 'res.partner'

    cnic = fields.Char(string="CNIC")
    buyer_registration_type = fields.Selection([
        ('Registered', 'Registered'),
        ('Unregistered', 'Unregistered')
    ], string='Registration Type', compute='_compute_registration_type', store=True)
    
    @api.depends('vat', 'cnic')
    def _compute_registration_type(self):
        for partner in self:
            partner.buyer_registration_type = 'Registered' if partner.vat else 'Unregistered'


class FBRReferenceData(models.Model):
    """Store FBR reference data locally"""
    _name = 'fbr.reference.data'
    _description = 'FBR Reference Data'
    
    name = fields.Char(string='Name', required=True)
    code = fields.Char(string='Code', required=True)
    data_type = fields.Selection([
        ('province', 'Province'),
        ('hs_code', 'HS Code'),
        ('uom', 'Unit of Measurement'),
        ('rate', 'Tax Rate')
    ], string='Data Type', required=True)
    description = fields.Text(string='Description')
    active = fields.Boolean(string='Active', default=True)
    
    _sql_constraints = [
        ('unique_code_type', 'UNIQUE(code, data_type)', 
         'Code must be unique per data type!')
    ]


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    # Enhanced fields with dropdowns
    fbr_hs_code_id = fields.Many2one(
        'fbr.reference.data',
        string="HS Code",
        domain=[('data_type', '=', 'hs_code')],
        help="Select HS code from FBR master data"
    )
    pct_code = fields.Char(
        string="PCT/HS Code", 
        related='fbr_hs_code_id.code',
        store=True,
        readonly=True
    )
    
    fbr_uom_id = fields.Many2one(
        'fbr.reference.data',
        string="FBR UOM",
        domain=[('data_type', '=', 'uom')],
        help="Select UOM from FBR master data"
    )
    
    # In product.product or product.template
class ProductTemplate(models.Model):
    _inherit = 'product.template'
    
    sale_type = fields.Selection([
        ('Goods at standard rate (default)', 'Goods at Standard Rate'),
        ('Goods at Reduced Rate', 'Goods at Reduced Rate'),
        ('Exempt Goods', 'Exempt Goods'),
        ('Goods at zero-rate', 'Goods at Zero Rate'),  # Make sure this matches
        ('Services', 'Services'),
    ], string='Sale Type', required=True, default='Goods at standard rate (default)')
    
    sro_schedule = fields.Char(string='SRO Schedule No')
    sro_item = fields.Char(string='SRO Item No')
    fed_duty = fields.Many2one('account.tax', string='FED Duty')
    further_tax = fields.Many2one('account.tax', string='Further Tax')
    extra_tax = fields.Many2one('account.tax', string='Extra Tax')
    other_tax = fields.Char(string='Other Type Tax')
    withholding_tax = fields.Many2one('account.tax', string='Withholding Tax')