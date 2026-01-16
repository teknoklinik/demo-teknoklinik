from odoo import models, fields, api

class KabulRapor(models.Model):
    _name = 'kabul.rapor'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'

    # Otomatik değil, manuel giriş için readonly=False yaptık
    name = fields.Char(string='Kabul Numarası', required=True, tracking=True)
    servis_id = fields.Many2one('servis.kaydi', string='İlgili Servis Kaydı')
    musteri_id = fields.Many2one('res.partner', string='Müşteri', required=True)
    urun_id = fields.Many2one('servis.urun', string='Ürün')
    teknisyen_notu = fields.Text(string='Teknisyen Notu')

    # Kabul için özel alanlar
    ariza_aciklama = fields.Text(string='Arıza Açıklaması')
    ilk_muayene_notu = fields.Text(string='İlk Muayene Notu')
    
    kayit_tarihi = fields.Date(string='Kabul Tarihi', default=fields.Date.context_today)
    state = fields.Selection([
        ('taslak', 'Taslak'),
        ('kabul_edildi', 'Kabul Edildi'),
        ('reddedildi', 'Reddedildi')
    ], string='Durum', default='taslak', tracking=True)
    
    # Para Birimi
    company_id = fields.Many2one('res.company', string='Şirket', default=lambda self: self.env.company)
    company_currency_id = fields.Many2one('res.currency', string='Para Birimi', compute='_compute_company_currency_id', store=True)
    
    # Parça ve Hizmetler Tablosu
    line_ids = fields.One2many('kabul.rapor.line', 'rapor_id', string='Parçalar ve Hizmetler')
    
    # Toplam Alanları
    amount_untaxed = fields.Float(string='Ara Toplam', compute='_compute_amounts', store=True)
    amount_tax = fields.Float(string='Vergi', compute='_compute_amounts', store=True)
    amount_total = fields.Float(string='Genel Toplam', compute='_compute_amounts', store=True)

    # Müşteri imzası için binary alan
    musteri_imzasi = fields.Binary(string='Müşteri İmzası', copy=False)

    @api.depends('company_id')
    def _compute_company_currency_id(self):
        for record in self:
            record.company_currency_id = record.company_id.currency_id

    @api.depends('line_ids.price_subtotal')
    def _compute_amounts(self):
        for record in self:
            untaxed = sum(line.price_subtotal for line in record.line_ids)
            record.amount_untaxed = untaxed
            record.amount_tax = untaxed * 0.20  # %20 KDV varsayılan
            record.amount_total = untaxed + record.amount_tax
    
class KabulRaporLine(models.Model):
    _name = 'kabul.rapor.line'
    _description = 'Kabul Rapor Satırları'

    rapor_id = fields.Many2one('kabul.rapor', string='Kabul Rapor', ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Ürün/Hizmet', required=True)
    qty = fields.Float(string='Adet', default=1.0)
    price_unit = fields.Float(string='Birim Fiyat')
    price_subtotal = fields.Float(string='Alt Toplam', compute='_compute_subtotal', store=True)

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            self.price_unit = self.product_id.lst_price

    @api.depends('qty', 'price_unit')
    def _compute_subtotal(self):
        for line in self:
            line.price_subtotal = line.qty * line.price_unit


