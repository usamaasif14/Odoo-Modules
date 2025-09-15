from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from datetime import timedelta
import requests
import json
import traceback
import base64
from io import BytesIO


def generate_qr_code(value):
    """Generate QR code with fallback"""
    try:
        import qrcode
        qr = qrcode.QRCode(version=1, box_size=20, border=4)
        qr.add_data(value)
        qr.make(fit=True)
        img = qr.make_image()
        stream = BytesIO()
        img.save(stream, format="PNG")
        return base64.b64encode(stream.getvalue())
    except ImportError:
        # QR library not available
        return None


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    # Enhanced fields with dropdown support
    fbr_hs_code_id = fields.Many2one(
        'fbr.reference.data',
        string="HS Code",
        domain=[('data_type', '=', 'hs_code')]
    )
    pct_code = fields.Char(
        string="PCT/HS Code",
        related='fbr_hs_code_id.code',
        store=True
    )
    
    fbr_uom_id = fields.Many2one(
        'fbr.reference.data',
        string="FBR UOM",
        domain=[('data_type', '=', 'uom')]
    )
    
    sale_type = fields.Selection([
        ('Goods at standard rate (default)', 'Goods at Standard Rate'),
        ('Services', 'Services'),
    ], string='Sale Type', default='Goods at standard rate (default)')
    
    sro_schedule = fields.Char(string='SRO Schedule No')
    sro_item = fields.Char(string='SRO Item No')
    fed_duty = fields.Many2one('account.tax', string='FED Duty')
    further_tax = fields.Many2one('account.tax', string='Further Tax')
    extra_tax = fields.Many2one('account.tax', string='Extra Tax')
    other_tax = fields.Char(string='Other Type Tax')
    withholding_tax = fields.Many2one('account.tax', string='Withholding Tax')

    @api.onchange('product_id')
    def _onchange_product_id_fbr_fields(self):
        """Auto-populate FBR fields from product"""
        if self.product_id:
            self.fbr_hs_code_id = self.product_id.fbr_hs_code_id
            self.fbr_uom_id = self.product_id.fbr_uom_id
            self.sale_type = self.product_id.sale_type
            self.sro_schedule = self.product_id.sro_schedule
            self.sro_item = self.product_id.sro_item
            self.fed_duty = self.product_id.fed_duty
            self.further_tax = self.product_id.further_tax
            self.extra_tax = self.product_id.extra_tax
            self.withholding_tax = self.product_id.withholding_tax
            self.other_tax = self.product_id.other_tax


class AccountMove(models.Model):
    _inherit = 'account.move'

    fbr_request = fields.Text("FBR Request", copy=False)
    fbr_response = fields.Text("FBR Response", copy=False)
    fbr_status = fields.Selection([
        ('draft', 'Draft'),
        ('sent', 'Sent'),
        ('verified', 'Verified'),
        ('failed', 'Failed')
    ], string="FBR Status", default="draft", copy=False)
    fbr_invoice_number = fields.Char("FBR Invoice Number", copy=False)
    fbr_post_successful = fields.Boolean("FBR Data Posted", copy=False)
    scenario_id = fields.Char(string='Scenario ID')
    fbr_qr_image = fields.Binary(string="QR Code", copy=False)
    display_scenario = fields.Boolean(string='Display Scenario', compute='_display_scenario_field')

    def _display_scenario_field(self):
        for rec in self:
            config = self.env['ir.config_parameter'].sudo()
            fbr_mode = config.get_param('fbr_integration.fbr_mode')
            rec.display_scenario = fbr_mode == 'sandbox'

    def _generate_qr_code(self):
        """Generate QR code for FBR invoice"""
        for order in self:
            if not order.fbr_invoice_number:
                continue
                
            qr_data = f"FBR Invoice: {order.fbr_invoice_number}\nSeller: {order.company_id.name}\nAmount: {order.amount_total}"
            qr_img = generate_qr_code(qr_data)
            if qr_img:
                order.fbr_qr_image = qr_img

    def action_post_data_to_fbr(self):
        """Send invoice data to FBR"""
        for invoice in self:
            if invoice.state != 'posted':
                raise ValidationError(_('Please post the invoice first.'))

            config = self.env['ir.config_parameter'].sudo()
            fbr_auth_token = config.get_param('fbr_integration.fbr_token')
            fbr_mode = config.get_param('fbr_integration.fbr_mode')

            if not fbr_auth_token:
                raise ValidationError(_('FBR Token not configured in settings.'))

            # Prepare payload
            fbr_payload = invoice._prepare_fbr_payload(fbr_mode)
            
            # Send to FBR
            try:
                invoice._send_to_fbr_api(fbr_payload, fbr_auth_token, fbr_mode)
                if invoice.fbr_invoice_number:
                    invoice._generate_qr_code()
            except Exception as e:
                raise UserError(_('FBR submission failed: %s') % str(e))

    def _prepare_fbr_payload(self, fbr_mode):
        """Prepare FBR API payload"""
        items_data = []

        for line in self.invoice_line_ids:
            # Get values with fallbacks
            hs_code = line.fbr_hs_code_id.code if line.fbr_hs_code_id else "0000.0000"
            uom_name = line.fbr_uom_id.name if line.fbr_uom_id else "Numbers"
            
            # Calculate tax amounts
            price_subtotal = abs(line.price_subtotal)
            price_total = abs(line.price_total)
            tax_amount = price_total - price_subtotal
            
            items_data.append({
                "hsCode": hs_code,
                "productDescription": line.product_id.name or line.name or "",
                "ProductCode": line.product_id.default_code or "",
                "rate": "18%",  # Default rate
                "uoM": uom_name,
                "quantity": abs(line.quantity),
                "totalValues": price_total,
                "valueSalesExcludingST": price_subtotal,
                "salesTaxApplicable": tax_amount,
                "fixedNotifiedValueOrRetailPrice": 0,
                "salesTaxWithheldAtSource": 0,
                "extraTax": 0,
                "furtherTax": 0,
                "sroScheduleNo": line.sro_schedule or "",
                "fedPayable": 0,
                "discount": 0,
                "saleType": line.sale_type or "Goods at standard rate (default)",
                "sroItemSerialNo": line.sro_item or ""
            })

        payload = {
            "invoiceDate": self.invoice_date.strftime("%Y-%m-%d") if self.invoice_date else fields.Date.today().strftime("%Y-%m-%d"),
            "sellerBusinessName": self.company_id.name or "",
            "sellerProvince": self.company_id.state_id.name or "Punjab",
            "sellerAddress": self.company_id.street or "",
            "sellerNTNCNIC": self.company_id.vat or "",
            "buyerNTNCNIC": self.partner_id.vat or self.partner_id.cnic or "",
            "buyerBusinessName": self.partner_id.name or "",
            "buyerProvince": self.partner_id.state_id.name or "Punjab",
            "buyerAddress": self.partner_id.street or "",
            "buyerRegistrationType": self.partner_id.buyer_registration_type or "Unregistered",
            "items": items_data,
            "invoiceType": "Sale Invoice"
        }

        if fbr_mode == 'sandbox':
            payload['scenarioId'] = self.scenario_id or "SN001"

        return payload

    def _send_to_fbr_api(self, payload, token, mode):
        """Send payload to FBR API"""
        url = ("https://gw.fbr.gov.pk/di_data/v1/di/postinvoicedata_sb" if mode == 'sandbox' 
               else "https://gw.fbr.gov.pk/di_data/v1/di/postinvoicedata")
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
        }
        
        self.fbr_request = json.dumps(payload, indent=4)
        
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        result = response.json()
        
        self.fbr_response = json.dumps(result, indent=4)
        
        if response.status_code == 200 and result.get('invoiceNumber'):
            self.fbr_invoice_number = result['invoiceNumber']
            self.fbr_status = 'verified'
            self.fbr_post_successful = True
        else:
            self.fbr_status = 'failed'
            self.fbr_post_successful = False
            error_msg = result.get('validationResponse', {}).get('error', 'Unknown error')
            raise ValidationError(f"FBR API Error: {error_msg}")