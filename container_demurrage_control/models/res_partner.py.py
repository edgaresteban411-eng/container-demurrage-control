from odoo import models, fields, api

class ResPartner(models.Model):
    _inherit = 'res.partner'

    is_shipping_line = fields.Boolean(string="Es Naviera", default=False)
    admin_fee_percent = fields.Float(string="% de Administración", default=10.0)
    special_free_days_ids = fields.One2many(
        'demurrage.partner.free.days', 'partner_id', string="Días Libres Especiales"
    )

class DemurragePartnerFreeDays(models.Model):
    _name = 'demurrage.partner.free.days'
    _description = 'Días Libres Especiales por Cliente y Naviera'

    partner_id = fields.Many2one('res.partner', required=True, ondelete='cascade')
    shipping_line_id = fields.Many2one(
        'res.partner', domain="[('is_shipping_line', '=', True)]", required=True, string="Naviera"
    )
    extra_free_days = fields.Integer(string="Días Libres Extra", default=0)