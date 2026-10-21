from odoo import models, fields, api

class DemurrageBL(models.Model):
    _name = 'demurrage.bl'
    _description = 'Bill of Lading (BL)'

    name = fields.Char(string="Número de BL", required=True, index=True)
    client_id = fields.Many2one('res.partner', string="Cliente", required=True)
    shipping_line_id = fields.Many2one(
        'res.partner', domain="[('is_shipping_line', '=', True)]", string="Naviera", required=True
    )
    discharge_date = fields.Date(string="Fecha de Descarga General", required=True, default=fields.Date.today)
    container_ids = fields.One2many('demurrage.container', 'bl_id', string="Contenedores")

    @api.onchange('discharge_date')
    def _onchange_discharge_date(self):
        for line in self.container_ids:
            if not line.discharge_date:
                line.discharge_date = self.discharge_date