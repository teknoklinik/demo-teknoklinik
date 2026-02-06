from odoo import models, fields, api, _
import random

class ServisArizaTanimi(models.Model):
    _name = 'servis.ariza.tanimi'
    _description = 'Servis Arıza Tanımları'
    _rec_name = 'name'
    name = fields.Char(string='Arıza Adı', required=True)
    urun_turu_id = fields.Many2one('urun.turu', string='Ürün Tipi')
    aktif = fields.Boolean(string='Aktif', default=True)

class ServisKaydiArizaDetay(models.Model):
    _name = 'servis.kaydi.ariza.detay'
    _description = 'Servis Kaydı Arıza Detayları'
    servis_kaydi_id = fields.Many2one('servis.kaydi', string='Servis Kaydı', required=True, ondelete='cascade')
    ariza_tanimi_id = fields.Many2one(
        'servis.ariza.tanimi', 
        string='Arıza Tipi', 
        required=True,
        domain="[('aktif', '=', True), ('urun_turu_id', '=', parent.urun_turu_id)]"
    )
    musteri_notu = fields.Char(string='Müşteri Notu') 

class ServisKaydiTeknikRaporSatir(models.Model):
    _name = 'servis.kaydi.teknik.rapor.satir'
    _description = 'Parça ve Hizmet Satırları'
    _order = 'sequence, id'

    servis_kaydi_id = fields.Many2one('servis.kaydi', string='Servis Kaydı', required=True, ondelete='cascade')
    sequence = fields.Integer(string='Sıra', default=10)
    
    ornek_tur = fields.Selection([
        ('hizmet', 'Hizmet'),
        ('yedek_parca', 'Yedek Parça'),
        ('diger', 'Diğer')
    ], string='Tür', required=True, default='hizmet')
    
    ornek_urun_id = fields.Many2one('product.product', string='Ürün')
    ornek_aciklama = fields.Char(string='Açıklama', required=True)
    ornek_miktar = fields.Float(string='Miktar', default=1.0, required=True)
    
    currency_id = fields.Many2one(related='servis_kaydi_id.company_currency_id', store=True, readonly=True)
    ornek_birim_fiyat = fields.Monetary(string='Birim Fi.', required=True, currency_field='currency_id')
    ornek_vergiler = fields.Many2many('account.tax', string='Vergiler', domain="[('type_tax_use', '=', 'sale')]")
    
    ornek_ara_toplam = fields.Monetary(
        string='Ara Toplam',
        compute='_compute_ara_toplam',
        store=True,
        currency_field='currency_id'
    )

    @api.depends('ornek_miktar', 'ornek_birim_fiyat', 'ornek_vergiler')
    def _compute_ara_toplam(self):
        """Satır bazında vergi hariç ara toplamı hesaplar."""
        for line in self:
            # compute_all metodunu kullanarak vergi hariç (total_excluded) tutarı alıyoruz
            taxes = line.ornek_vergiler.compute_all(
                line.ornek_birim_fiyat, 
                quantity=line.ornek_miktar, 
                currency=line.currency_id, 
                product=line.ornek_urun_id, 
                partner=line.servis_kaydi_id.musteri_id
            )
            line.ornek_ara_toplam = taxes['total_excluded']

    @api.onchange('ornek_urun_id')
    def _onchange_ornek_urun_id(self):
        """Ürün seçildiğinde fiyat, açıklama ve vergileri otomatik doldurur."""
        if self.ornek_urun_id:
            self.ornek_aciklama = self.ornek_urun_id.display_name
            self.ornek_birim_fiyat = self.ornek_urun_id.list_price
            self.ornek_vergiler = self.ornek_urun_id.taxes_id  # Vergileri otomatik getirir
            
            if not self.ornek_miktar:
                self.ornek_miktar = 1.0
        else:
            self.ornek_birim_fiyat = 0.0
            self.ornek_vergiler = False

    @api.onchange('ornek_tur')
    def _onchange_ornek_tur(self):
        """Tür seçimine göre ürün listesini filtreler."""
        if self.ornek_tur == 'hizmet':
            return {'domain': {'ornek_urun_id': [('type', '=', 'service')]}}
        else:
            return {'domain': {'ornek_urun_id': [('type', 'in', ['product', 'consu'])]}}
        
class ServisKaydiNotlar(models.Model):
    _name = 'servis.kaydi.notlar'
    _description = 'Servis Kaydı Notlar'

    servis_kaydi_id = fields.Many2one('servis.kaydi', string='Servis Kaydı', required=True, ondelete='cascade')
    konu = fields.Char(string='Konu')
    aciklama = fields.Text(string='Açıklama')
    not_personel_id = fields.Many2one('res.users', string='İlgili Personel', 
                                      default=lambda self: self.env.user, readonly=True)
    not_kayit_tarihi = fields.Datetime(string='Tarih', 
                                       default=fields.Datetime.now, readonly=True)

    def action_save_and_reload(self):
        """Kaydeder ve sayfayı yeniler"""
        self.ensure_one()
        return {'type': 'ir.actions.client', 'tag': 'reload'}
    
    def action_close_wizard(self):
        return {'type': 'ir.actions.act_window_close'}

class ServisKaydiDokuman(models.Model):
    _name = 'servis.kaydi.dokuman'
    _description = 'Servis Kaydı Dokümanları'

    servis_kaydi_id = fields.Many2one('servis.kaydi', string='Servis Kaydı', required=True, ondelete='cascade')
    konu = fields.Char(string='Konu', required=True)
    dokuman_dosya = fields.Binary(string='Dosya', filename='dokuman_dosya_isim', required=True)
    dokuman_dosya_isim = fields.Char(string='Dosya Adı')
    
    dokuman_personel_id = fields.Many2one('res.users', string='Yükleyen Personel', 
                                           default=lambda self: self.env.user, readonly=True)
    dokuman_tarihi = fields.Datetime(string='Yükleme Tarihi', 
                                     default=fields.Datetime.now, readonly=True)

    def action_save_and_reload(self):
        """Kaydeder ve sayfayı yeniler (F5 etkisi)"""
        self.ensure_one()
        return {'type': 'ir.actions.client', 'tag': 'reload'}
    
    def action_preview_document(self):
        """Dokümanı tarayıcıda önizlemek için URL döner"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content/?model=servis.kaydi.dokuman&id=%s&field=dokuman_dosya&filename_field=dokuman_dosya_isim&download=false' % (self.id),
            'target': 'new', 
        }
    
    def action_close_popup(self):
        return {'type': 'ir.actions.act_window_close'}

class ServisEtiket(models.Model):
    _name = 'servis.etiket'
    _description = 'Servis Kaydı Etiketleri'

    def _get_default_color(self):
        return random.randint(1, 11)

    name = fields.Char(string='Etiket Adı', required=True)
    color = fields.Integer(string='Renk İndeksi', default=_get_default_color)

