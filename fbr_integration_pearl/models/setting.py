from odoo import models, fields, api, _


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    fbr_mode = fields.Selection([
        ('sandbox', 'Sandbox'),
        ('production', 'Production')
    ], string="FBR Environment", default='sandbox')
    fbr_token = fields.Char(string="FBR API Token")
    fbr_bpos_id = fields.Char(string="FBR BPOS ID", default="05")
    fbr_enable_service = fields.Boolean(string='Enable Service Fee?')
    fbr_service_fee = fields.Float(string='Service Fee')
    fbr_auto_sync = fields.Boolean(string='Auto Sync FBR Data')

    def set_values(self):
        super().set_values()
        params = self.env['ir.config_parameter'].sudo()
        params.set_param('fbr_integration.fbr_mode', self.fbr_mode)
        params.set_param('fbr_integration.fbr_token', self.fbr_token)
        params.set_param('fbr_integration.fbr_bpos_id', self.fbr_bpos_id)
        params.set_param('fbr_integration.fbr_enable_service', self.fbr_enable_service)
        params.set_param('fbr_integration.fbr_service_fee', self.fbr_service_fee)
        params.set_param('fbr_integration.fbr_auto_sync', self.fbr_auto_sync)

    def get_values(self):
        res = super().get_values()
        params = self.env['ir.config_parameter'].sudo()
        res.update(
            fbr_mode=params.get_param('fbr_integration.fbr_mode'),
            fbr_token=params.get_param('fbr_integration.fbr_token'),
            fbr_bpos_id=params.get_param('fbr_integration.fbr_bpos_id'),
            fbr_enable_service=params.get_param('fbr_integration.fbr_enable_service'),
            fbr_service_fee=params.get_param('fbr_integration.fbr_service_fee'),
            fbr_auto_sync=params.get_param('fbr_integration.fbr_auto_sync'),
        )
        return res

    def action_sync_fbr_data(self):
        """Manual sync trigger"""
        sync_obj = self.env['fbr.data.sync']
        result = sync_obj.sync_reference_data()
        
        if result:
            message = _('FBR reference data synced successfully!')
            msg_type = 'success'
        else:
            message = _('Sync failed. Please check your FBR token and connection.')
            msg_type = 'warning'
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('FBR Data Sync'),
                'message': message,
                'type': msg_type,
                'sticky': False,
            }
        }