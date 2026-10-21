from odoo import models, fields, api

class DemurrageRate(models.Model):
    _name = 'demurrage.rate'
    _description = 'Tarifas de Demoras de Navieras'

    shipping_line_id = fields.Many2one(
        'res.partner', domain="[('is_shipping_line', '=', True)]", required=True, string="Naviera"
    )
    container_type = fields.Selection([
        ('20DV', '20DV - 20 pies estándar'),
        ('40DV', '40DV - 40 pies estándar'),
        ('40HC', '40HC - 40 pies High Cube'),
        ('40RF', '40RF - 40 pies refrigerado'),
    ], required=True, string="Tipo de Contenedor")
    
    start_date = fields.Date(string="Vigencia Desde", required=True)
    end_date = fields.Date(string="Vigencia Hasta")
    free_days = fields.Integer(string="Días Libres Naviera", required=True, default=0)
    tier_ids = fields.One2many('demurrage.rate.tier', 'rate_id', string="Tramos de Tarifa")

class DemurrageRateTier(models.Model):
    _name = 'demurrage.rate.tier'
    _description = 'Tramo de Tarifa de Demora'
    _order = 'day_start asc'

    rate_id = fields.Many2one('demurrage.rate', required=True, ondelete='cascade')
    day_start = fields.Integer(string="Día Inicio Tramo", required=True)
    day_end = fields.Integer(string="Día Fin Tramo (0 = Indefinido)")
    daily_rate_usd = fields.Float(string="Tarifa USD / Día", required=True)