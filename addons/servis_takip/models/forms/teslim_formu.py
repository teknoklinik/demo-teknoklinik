from odoo import models, fields, api

class TeslimFormu(models.Model):
    _name = 'teslim.formu'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'

    # Otomatik değil, manuel giriş için readonly=False yaptık
    name = fields.Char(string='Teslim Numarası', required=True, tracking=True)
    servis_id = fields.Many2one('servis.kaydi', string='İlgili Servis Kaydı')
    musteri_id = fields.Many2one('res.partner', string='Müşteri', required=True)
    urun_id = fields.Many2one('servis.urun', string='Ürün')
    teknisyen_notu = fields.Text(string='Teknisyen Notu')

    kayit_tarihi = fields.Date(string='Teslim Tarihi', default=fields.Date.context_today)
    state = fields.Selection([
        ('taslak', 'Taslak'),
        ('devam_ediyor', 'İşlemde'),
        ('tamamlandi', 'Tamamlandı'),
        ('iptal', 'İptal')
    ], string='Durum', default='taslak', tracking=True)
    
    # Para Birimi
    company_id = fields.Many2one('res.company', string='Şirket', default=lambda self: self.env.company)
    company_currency_id = fields.Many2one('res.currency', string='Para Birimi', compute='_compute_company_currency_id', store=True)
    
    # Parça ve Hizmetler Tablosu
    line_ids = fields.One2many('teslim.formu.line', 'formu_id', string='Parçalar ve Hizmetler')
    
    # Toplam Alanları
    amount_untaxed = fields.Float(string='Ara Toplam', compute='_compute_amounts', store=True)
    amount_tax = fields.Float(string='Vergi', compute='_compute_amounts', store=True)
    amount_total = fields.Float(string='Genel Toplam', compute='_compute_amounts', store=True)

    # Müşteri imzası için binary alan
    musteri_imzasi = fields.Binary(string='Müşteri İmzası', copy=False)
    teslim_musteri_imzasi = fields.Binary(string='Teslim Müşteri İmzası', copy=False)
    
    # Ürün detayları
    seri_no = fields.Char(string='Seri No')
    teslim_tarihi = fields.Date(string='Teslim Tarihi')
    
    # Arıza detay satırları
    ariza_detay_ids = fields.One2many('teslim.formu.ariza', 'formu_id', string='Arıza Detayları')
    
    # Servis işlem satırları
    servis_islem_satirlari = fields.One2many('teslim.formu.islem', 'formu_id', string='Servis İşlem Satırları')
    
    # Değer okuma satırları
    deger_okuma_ids = fields.One2many('teslim.formu.deger.okuma', 'formu_id', string='Değer Okuma Verileri')

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
    
class TeslimFormuLine(models.Model):
    _name = 'teslim.formu.line'
    _description = 'Teslim Formu Satırları'

    formu_id = fields.Many2one('teslim.formu', string='Teslim Formu', ondelete='cascade')
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


class TeslimFormuAriza(models.Model):
    _name = 'teslim.formu.ariza'
    _description = 'Teslim Formu Arıza Detayları'

    formu_id = fields.Many2one('teslim.formu', string='Teslim Formu', ondelete='cascade')
    ariza_tanimi_id = fields.Many2one('servis.ariza.tanimi', string='Arıza Tanımı')
    musteri_notu = fields.Text(string='Müşteri Notu')


class TeslimFormuIslem(models.Model):
    _name = 'teslim.formu.islem'
    _description = 'Teslim Formu Servis İşlem Satırları'

    formu_id = fields.Many2one('teslim.formu', string='Teslim Formu', ondelete='cascade')
    islem_aciklama = fields.Text(string='İşlem Açıklaması')
    islem_tarihi = fields.Date(string='İşlem Tarihi')


class TeslimFormuDegerOkuma(models.Model):
    _name = 'teslim.formu.deger.okuma'
    _description = 'Teslim Formu Değer Okuma Verileri'

    formu_id = fields.Many2one('teslim.formu', string='Teslim Formu', ondelete='cascade')
    deger_okuma_tanimi_id = fields.Many2one('deger.okuma.tanimi', string='Değer Okuma', required=True)
    aciklama = fields.Text(string='Açıklama')
    tarih = fields.Datetime(string='Tarih', default=lambda self: fields.Datetime.now())
    personel_id = fields.Many2one('hr.employee', string='İlgili Personel')


