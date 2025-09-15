from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import requests
import json
import logging

_logger = logging.getLogger(__name__)


class FBRDataSync(models.Model):
    """Handle FBR data synchronization"""
    _name = 'fbr.data.sync'
    _description = 'FBR Data Synchronization'
    
    name = fields.Char(string='Sync Name', default='FBR Data Sync')
    last_sync_date = fields.Datetime(string='Last Sync Date')
    sync_status = fields.Selection([
        ('success', 'Success'),
        ('failed', 'Failed'),
        ('in_progress', 'In Progress')
    ], string='Status', default='success')
    sync_log = fields.Text(string='Sync Log')
    
    @api.model
    def _get_fbr_headers(self):
        """Get FBR API headers"""
        config = self.env['ir.config_parameter'].sudo()
        fbr_token = config.get_param('fbr_integration.fbr_token')
        if not fbr_token:
            raise ValidationError(_('FBR Token not configured in settings.'))
        
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {fbr_token}",
        }
    
    @api.model
    def sync_provinces(self):
        """Sync provinces from FBR API"""
        try:
            headers = self._get_fbr_headers()
            response = requests.get(
                'https://gw.fbr.gov.pk/pdi/v1/provinces',
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 200:
                provinces = response.json()
                reference_obj = self.env['fbr.reference.data']
                
                for province in provinces:
                    existing = reference_obj.search([
                        ('code', '=', str(province['stateProvinceCode'])),
                        ('data_type', '=', 'province')
                    ])
                    
                    vals = {
                        'name': province['stateProvinceDesc'],
                        'code': str(province['stateProvinceCode']),
                        'data_type': 'province',
                        'description': province['stateProvinceDesc'],
                    }
                    
                    if existing:
                        existing.write(vals)
                    else:
                        reference_obj.create(vals)
                
                _logger.info("Successfully synced %d provinces", len(provinces))
                return True
            else:
                _logger.error("Failed to sync provinces: HTTP %d", response.status_code)
                return False
                
        except Exception as e:
            _logger.error("Error syncing provinces: %s", str(e))
            return False
    
    @api.model
    def sync_hs_codes(self):
        """Sync HS codes from FBR API"""
        try:
            headers = self._get_fbr_headers()
            response = requests.get(
                'https://gw.fbr.gov.pk/pdi/v1/itemdesccode',
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 200:
                hs_codes = response.json()
                reference_obj = self.env['fbr.reference.data']
                
                # Limit to first 100 for performance
                for hs_code in hs_codes[:100]:
                    existing = reference_obj.search([
                        ('code', '=', hs_code['hS_CODE']),
                        ('data_type', '=', 'hs_code')
                    ])
                    
                    name = f"{hs_code['hS_CODE']} - {hs_code['description'][:50]}..."
                    vals = {
                        'name': name,
                        'code': hs_code['hS_CODE'],
                        'data_type': 'hs_code',
                        'description': hs_code['description'],
                    }
                    
                    if existing:
                        existing.write(vals)
                    else:
                        reference_obj.create(vals)
                
                _logger.info("Successfully synced HS codes")
                return True
            else:
                _logger.error("Failed to sync HS codes: HTTP %d", response.status_code)
                return False
                
        except Exception as e:
            _logger.error("Error syncing HS codes: %s", str(e))
            return False
    
    @api.model
    def sync_uoms(self):
        """Sync UOMs from FBR API"""
        try:
            headers = self._get_fbr_headers()
            response = requests.get(
                'https://gw.fbr.gov.pk/pdi/v1/uom',
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 200:
                uoms = response.json()
                reference_obj = self.env['fbr.reference.data']
                
                for uom in uoms:
                    existing = reference_obj.search([
                        ('code', '=', str(uom['uoM_ID'])),
                        ('data_type', '=', 'uom')
                    ])
                    
                    vals = {
                        'name': uom['description'],
                        'code': str(uom['uoM_ID']),
                        'data_type': 'uom',
                        'description': uom['description'],
                    }
                    
                    if existing:
                        existing.write(vals)
                    else:
                        reference_obj.create(vals)
                
                _logger.info("Successfully synced UOMs")
                return True
            else:
                _logger.error("Failed to sync UOMs: HTTP %d", response.status_code)
                return False
                
        except Exception as e:
            _logger.error("Error syncing UOMs: %s", str(e))
            return False
    
    @api.model
    def sync_reference_data(self):
        """Sync all reference data"""
        results = {
            'provinces': self.sync_provinces(),
            'hs_codes': self.sync_hs_codes(),
            'uoms': self.sync_uoms(),
        }
        
        # Update sync record
        sync_record = self.search([], limit=1)
        if not sync_record:
            sync_record = self.create({'name': 'FBR Data Sync'})
        
        sync_record.write({
            'last_sync_date': fields.Datetime.now(),
            'sync_status': 'success' if all(results.values()) else 'failed',
            'sync_log': json.dumps(results, indent=2)
        })
        
        return all(results.values())