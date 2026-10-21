from odoo import models, fields, api
from odoo.exceptions import ValidationError, UserError
from datetime import date

def validate_iso_6346(code):
    if not code or len(code) != 11:
        return False
    code = code.upper()
    if code[3] not in ['U', 'J', 'Z']:
        return False
    
    char_map = {
        'A': 10, 'B': 12, 'C': 13, 'D': 14, 'E': 15, 'F': 16, 'G': 17, 'H': 18, 'I': 19,
        'J': 20, 'K': 21, 'L': 23, 'M': 24, 'N': 25, 'O': 26, 'P': 27, 'Q': 28, 'R': 29,
        'S': 30, 'T': 31, 'U': 32, 'V': 34, 'W': 35, 'X': 36, 'Y': 37, 'Z': 38
    }
    
    total = 0
    for i in range(10):
        char = code[i]
        val = int(char) if char.isdigit() else char_map.get(char, 0)
        total += val * (2 ** i)
        
    check_digit = (total % 11) % 10
    return check_digit == int(code[10])

class DemurrageContainer(models.Model):
    _name = 'demurrage.container'
    _description = 'Contenedor en Control de Demoras'

    name = fields.Char(string="Número de Contenedor", required=True)
    bl_id = fields.Many2one('demurrage.bl', string="BL", required=True, ondelete='cascade')
    client_id = fields.Many2one(related='bl_id.client_id', store=True, readonly=True)
    shipping_line_id = fields.Many2one(related='bl_id.shipping_line_id', store=True, readonly=True)
    
    container_type = fields.Selection([
        ('20DV', '20DV'), ('40DV', '40DV'), ('40HC', '40HC'), ('40RF', '40RF')
    ], required=True, string="Tipo")
    
    discharge_date = fields.Date(string="Fecha Descarga", required=True)
    return_date = fields.Date(string="Fecha Devolución")
    
    eir_file = fields.Binary(string="Soporte EIR (PDF/Foto)")
    eir_filename = fields.Char(string="Nombre Archivo EIR")
    
    state = fields.Selection([
        ('draft', 'Borrador'),
        ('unreturned', 'Fuera (En Tránsito)'),
        ('returned', 'Devuelto'),
        ('invoiced', 'Facturado'),
    ], default='unreturned', string="Estado", required=True, tracking=True)

    days_out = fields.Integer(string="Días Afuera", compute='_compute_demurrage_calculations', store=True)
    free_days = fields.Integer(string="Días Libres Totales", compute='_compute_demurrage_calculations', store=True)
    demurrage_days = fields.Integer(string="Días Demora", compute='_compute_demurrage_calculations', store=True)
    shipping_cost_usd = fields.Float(string="Cobro Naviera (USD)", compute='_compute_demurrage_calculations', store=True)
    client_cost_usd = fields.Float(string="Cobro Cliente (USD)", compute='_compute_demurrage_calculations', store=True)
    is_estimated = fields.Boolean(string="Es Estimado", compute='_compute_demurrage_calculations', store=True)

    @api.constrains('name')
    def _check_iso_code(self):
        for rec in self:
            clean_name = rec.name.replace(" ", "").upper()
            if not validate_iso_6346(clean_name):
                raise ValidationError(f"El contenedor {rec.name} no cumple con la norma ISO 6346 (Dígito verificador inválido).")

    @api.constrains('return_date', 'discharge_date')
    def _check_dates(self):
        for rec in self:
            if rec.return_date:
                if rec.return_date < rec.discharge_date:
                    raise ValidationError("La fecha de devolución no puede ser anterior a la de descarga.")
                if rec.return_date > fields.Date.today():
                    raise ValidationError("La fecha de devolución no puede ser posterior a hoy.")

    @api.depends('discharge_date', 'return_date', 'container_type', 'shipping_line_id', 'client_id')
    def _compute_demurrage_calculations(self):
        eval_today = self.env.context.get('fixed_today') or fields.Date.today()
        
        for rec in self:
            if not rec.discharge_date or not rec.shipping_line_id or not rec.container_type:
                rec.days_out = rec.free_days = rec.demurrage_days = 0
                rec.shipping_cost_usd = rec.client_cost_usd = 0.0
                rec.is_estimated = False
                continue

            end_d = rec.return_date or eval_today
            rec.is_estimated = not bool(rec.return_date)
            
            rec.days_out = (end_d - rec.discharge_date).days + 1

            domain = [
                ('shipping_line_id', '=', rec.shipping_line_id.id),
                ('container_type', '=', rec.container_type),
                ('start_date', '<=', rec.discharge_date),
                '|', ('end_date', '=', False), ('end_date', '>=', rec.discharge_date)
            ]
            rate = self.env['demurrage.rate'].search(domain, limit=1)
            
            if not rate:
                rec.free_days = rec.demurrage_days = 0
                rec.shipping_cost_usd = rec.client_cost_usd = 0.0
                continue

            extra_days = 0
            if rec.client_id:
                spec = rec.client_id.special_free_days_ids.filtered(lambda x: x.shipping_line_id == rec.shipping_line_id)
                extra_days = sum(spec.mapped('extra_free_days'))
            
            rec.free_days = rate.free_days + extra_days
            rec.demurrage_days = max(0, rec.days_out - rec.free_days)

            total_shipping_usd = 0.0
            if rec.demurrage_days > 0:
                tiers = rate.tier_ids.sorted('day_start')
                for day_idx in range(1, rec.demurrage_days + 1):
                    day_rate = 0.0
                    for tier in tiers:
                        if day_idx >= tier.day_start and (tier.day_end == 0 or day_idx <= tier.day_end):
                            day_rate = tier.daily_rate_usd
                            break
                    total_shipping_usd += day_rate

            rec.shipping_cost_usd = total_shipping_usd
            
            margin = rec.client_id.admin_fee_percent if rec.client_id else 10.0
            rec.client_cost_usd = total_shipping_usd * (1.0 + (margin / 100.0))