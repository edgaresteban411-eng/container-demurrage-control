from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError
from datetime import date

class TestDemurrageCalculation(TransactionCase):

    def setUp(self):
        super(TestDemurrageCalculation, self).setUp()
        
        # 1. Crear Clientes
        self.partner_sol = self.env['res.partner'].create({
            'name': 'Importadora Sol S.A.S.',
            'admin_fee_percent': 10.0
        })
        self.partner_tornillo = self.env['res.partner'].create({
            'name': 'Ferretería El Tornillo S.A.S.',
            'admin_fee_percent': 10.0
        })
        self.partner_textiles = self.env['res.partner'].create({
            'name': 'Textiles Andinos Ltda.',
            'admin_fee_percent': 5.0
        })
        self.partner_frutas = self.env['res.partner'].create({
            'name': 'Frutas del Valle Export S.A.S.',
            'admin_fee_percent': 10.0
        })

        # 2. Crear Navieras
        self.nav_atlantico = self.env['res.partner'].create({
            'name': 'Naviera Atlántico',
            'is_shipping_line': True
        })
        self.nav_mar_sur = self.env['res.partner'].create({
            'name': 'Mar del Sur Line',
            'is_shipping_line': True
        })

        # 3. Días libres especiales
        self.env['demurrage.partner.free.days'].create({
            'partner_id': self.partner_tornillo.id,
            'shipping_line_id': self.nav_atlantico.id,
            'extra_free_days': 5
        })
        self.env['demurrage.partner.free.days'].create({
            'partner_id': self.partner_textiles.id,
            'shipping_line_id': self.nav_mar_sur.id,
            'extra_free_days': 3
        })

        # 4. Tarifas Naviera Atlántico
        rate_atlantico_40hc = self.env['demurrage.rate'].create({
            'shipping_line_id': self.nav_atlantico.id,
            'container_type': '40HC',
            'start_date': '2026-01-01',
            'free_days': 7
        })
        self.env['demurrage.rate.tier'].create([
            {'rate_id': rate_atlantico_40hc.id, 'day_start': 1, 'day_end': 5, 'daily_rate_usd': 60.0},
            {'rate_id': rate_atlantico_40hc.id, 'day_start': 6, 'day_end': 10, 'daily_rate_usd': 120.0},
            {'rate_id': rate_atlantico_40hc.id, 'day_start': 11, 'day_end': 0, 'daily_rate_usd': 180.0},
        ])

        rate_atlantico_20dv = self.env['demurrage.rate'].create({
            'shipping_line_id': self.nav_atlantico.id,
            'container_type': '20DV',
            'start_date': '2026-01-01',
            'free_days': 7
        })
        self.env['demurrage.rate.tier'].create([
            {'rate_id': rate_atlantico_20dv.id, 'day_start': 1, 'day_end': 5, 'daily_rate_usd': 35.0},
            {'rate_id': rate_atlantico_20dv.id, 'day_start': 6, 'day_end': 10, 'daily_rate_usd': 70.0},
            {'rate_id': rate_atlantico_20dv.id, 'day_start': 11, 'day_end': 0, 'daily_rate_usd': 110.0},
        ])

        rate_atlantico_40rf = self.env['demurrage.rate'].create({
            'shipping_line_id': self.nav_atlantico.id,
            'container_type': '40RF',
            'start_date': '2026-01-01',
            'free_days': 4
        })
        self.env['demurrage.rate.tier'].create([
            {'rate_id': rate_atlantico_40rf.id, 'day_start': 1, 'day_end': 5, 'daily_rate_usd': 150.0},
            {'rate_id': rate_atlantico_40rf.id, 'day_start': 6, 'day_end': 10, 'daily_rate_usd': 250.0},
        ])

        # 5. Tarifas Mar del Sur Line
        rate_marsur_40dv = self.env['demurrage.rate'].create({
            'shipping_line_id': self.nav_mar_sur.id,
            'container_type': '40DV',
            'start_date': '2026-01-01',
            'end_date': '2026-06-30',
            'free_days': 10
        })
        self.env['demurrage.rate.tier'].create([
            {'rate_id': rate_marsur_40dv.id, 'day_start': 1, 'day_end': 7, 'daily_rate_usd': 75.0},
            {'rate_id': rate_marsur_40dv.id, 'day_start': 8, 'day_end': 0, 'daily_rate_usd': 150.0},
        ])

        rate_marsur_20dv = self.env['demurrage.rate'].create({
            'shipping_line_id': self.nav_mar_sur.id,
            'container_type': '20DV',
            'start_date': '2026-07-01',
            'free_days': 8
        })
        self.env['demurrage.rate.tier'].create([
            {'rate_id': rate_marsur_20dv.id, 'day_start': 1, 'day_end': 7, 'daily_rate_usd': 45.0},
            {'rate_id': rate_marsur_20dv.id, 'day_start': 8, 'day_end': 0, 'daily_rate_usd': 95.0},
        ])

    def _create_container(self, client, naviera, cont_type, discharge, return_d=None, name="CSQU3054383"):
        bl = self.env['demurrage.bl'].create({
            'name': 'BL-TEST-001',
            'client_id': client.id,
            'shipping_line_id': naviera.id,
            'discharge_date': discharge
        })
        return self.env['demurrage.container'].create({
            'name': name,
            'bl_id': bl.id,
            'container_type': cont_type,
            'discharge_date': discharge,
            'return_date': return_d
        })

    # CASO 1
    def test_case_1(self):
        c = self._create_container(self.partner_sol, self.nav_atlantico, '40HC', '2026-03-02', '2026-03-20')
        self.assertEqual(c.days_out, 19)
        self.assertEqual(c.free_days, 7)
        self.assertEqual(c.demurrage_days, 12)
        self.assertAlmostEqual(c.shipping_cost_usd, 1260.0)
        self.assertAlmostEqual(c.client_cost_usd, 1386.0)

    # CASO 2
    def test_case_2(self):
        c = self._create_container(self.partner_tornillo, self.nav_atlantico, '20DV', '2026-04-10', '2026-04-21')
        self.assertEqual(c.days_out, 12)
        self.assertEqual(c.free_days, 12)
        self.assertEqual(c.demurrage_days, 0)
        self.assertAlmostEqual(c.shipping_cost_usd, 0.0)
        self.assertAlmostEqual(c.client_cost_usd, 0.0)

    # CASO 3
    def test_case_3(self):
        c = self._create_container(self.partner_textiles, self.nav_mar_sur, '40DV', '2026-06-28', '2026-07-15')
        self.assertEqual(c.days_out, 18)
        self.assertEqual(c.free_days, 13)
        self.assertEqual(c.demurrage_days, 5)
        self.assertAlmostEqual(c.shipping_cost_usd, 375.0)
        self.assertAlmostEqual(c.client_cost_usd, 393.75)

    # CASO 4
    def test_case_4(self):
        c = self._create_container(self.partner_frutas, self.nav_atlantico, '40RF', '2026-08-01', '2026-08-14')
        self.assertEqual(c.days_out, 14)
        self.assertEqual(c.free_days, 4)
        self.assertEqual(c.demurrage_days, 10)
        self.assertAlmostEqual(c.shipping_cost_usd, 2000.0)
        self.assertAlmostEqual(c.client_cost_usd, 2200.0)

    # CASO 5 (Estimado al 2026-09-20)
    def test_case_5(self):
        c = self._create_container(self.partner_sol, self.nav_mar_sur, '20DV', '2026-09-05', None)
        c_with_ctx = c.with_context(fixed_today=date(2026, 9, 20))
        c_with_ctx._compute_demurrage_calculations()
        self.assertEqual(c_with_ctx.days_out, 16)
        self.assertEqual(c_with_ctx.free_days, 8)
        self.assertEqual(c_with_ctx.demurrage_days, 8)
        self.assertAlmostEqual(c_with_ctx.shipping_cost_usd, 410.0)
        self.assertAlmostEqual(c_with_ctx.client_cost_usd, 451.0)
        self.assertTrue(c_with_ctx.is_estimated)

    # CASO 6
    def test_case_6(self):
        c = self._create_container(self.partner_sol, self.nav_atlantico, '20DV', '2026-05-04', '2026-05-10')
        self.assertEqual(c.days_out, 7)
        self.assertEqual(c.free_days, 7)
        self.assertEqual(c.demurrage_days, 0)
        self.assertAlmostEqual(c.shipping_cost_usd, 0.0)
        self.assertAlmostEqual(c.client_cost_usd, 0.0)

    # CASO 7
    def test_case_7(self):
        c = self._create_container(self.partner_sol, self.nav_atlantico, '20DV', '2026-05-04', '2026-05-11')
        self.assertEqual(c.days_out, 8)
        self.assertEqual(c.free_days, 7)
        self.assertEqual(c.demurrage_days, 1)
        self.assertAlmostEqual(c.shipping_cost_usd, 35.0)
        self.assertAlmostEqual(c.client_cost_usd, 38.5)

    # CASO 8
    def test_case_8(self):
        c = self._create_container(self.partner_sol, self.nav_atlantico, '20DV', '2026-09-14', '2026-09-14')
        self.assertEqual(c.days_out, 1)
        self.assertEqual(c.free_days, 7)
        self.assertEqual(c.demurrage_days, 0)
        self.assertAlmostEqual(c.shipping_cost_usd, 0.0)
        self.assertAlmostEqual(c.client_cost_usd, 0.0)

    # CASO 9 (Sin tarifa definida)
    def test_case_9(self):
        c = self._create_container(self.partner_frutas, self.nav_mar_sur, '40RF', '2026-08-03', '2026-08-20')
        self.assertEqual(c.shipping_cost_usd, 0.0)
        self.assertEqual(c.client_cost_usd, 0.0)