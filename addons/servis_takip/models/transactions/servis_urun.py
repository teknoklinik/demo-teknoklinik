from odoo import models, fields, api
from datetime import date
from dateutil.relativedelta import relativedelta
from odoo.exceptions import ValidationError

class ServisUrun(models.Model):
    _name = 'servis.urun'
    _description = 'Servis Ürün Kaydı'

    @api.onchange('tur_id', 'marka_id', 'model_id', 'serial_no')
    def _onchange_duplicate_product_check(self):
        # Dört alanın da dolu olduğundan emin olalım
        if self.tur_id and self.marka_id and self.model_id and self.serial_no:
            # ÖNEMLİ: Arama yaparken nesnelerin .id değerlerini kullanıyoruz
            existing_record = self.search([
                ('tur_id', '=', self.tur_id.id),
                ('marka_id', '=', self.marka_id.id),
                ('model_id', '=', self.model_id.id),
                ('serial_no', '=', self.serial_no),
                ('id', '!=', self.id if self.id else False)
            ], limit=1)

            if existing_record:
                return {
                    'warning': {
                        'title': "Mükerrer Kayıt Uyarısı!",
                        'message': "Bu Tür, Marka, Model ve Seri Numarasına sahip bir ürün zaten sistemde kayıtlı!",
                    }
                }
    
    @api.constrains('tur_id', 'marka_id', 'model_id', 'serial_no')
    def _check_unique_product(self):
        for record in self:
            # Tüm alanlar doluysa kontrol et
            if record.tur_id and record.marka_id and record.model_id and record.serial_no:
                # Veritabanında aynı kombinasyonu ara (kendisi hariç)
                exists = self.search([
                    ('tur_id', '=', record.tur_id.id),
                    ('marka_id', '=', record.marka_id.id),
                    ('model_id', '=', record.model_id.id),
                    ('serial_no', '=', record.serial_no),
                    ('id', '!=', record.id)
                ], limit=1)
                
                if exists:
                    # ValidationError fırlatmak işlemi tamamen durdurur, kaydetmez
                    raise ValidationError((
                        "KAYIT ENGELLENDİ!\n"
                        "Bu Tür, Marka, Model ve Seri Numarasına sahip bir ürün zaten sistemde mevcut. "
                        "Mükerrer kayıt oluşturamazsınız."
                    ))
    # *Ürün Kodu: Sequence ile otomatik artan
    name = fields.Char(string='Ürün Kodu', required=True, copy=False, readonly=True, index=True, default='Yeni')
    active = fields.Boolean(default=True)
    
    # *Temel Bilgiler
    tur_id = fields.Many2one('urun.turu', string='Ürün Türü', required=True)
    marka_id = fields.Many2one('urun.markasi', string='Marka', required=True, domain="[('tur_id', '=', tur_id)]")
    model_id = fields.Many2one('urun.modeli', string='Model', required=True, domain="[('marka_id', '=', marka_id)]")
    
    # *Seri No ve Diğerleri
    serial_no = fields.Char(string='Seri No', required=True)
    barcode = fields.Char(string='Barkod No')
    location = fields.Char(string='Lokasyon')

    etiket_ids = fields.Many2many('servis.etiket', string='Etiketler')
    
    # Müşteri Bilgileri
    musteri_tipi = fields.Selection([
        ('sahis', 'Şahıs'),
        ('sirket', 'Şirket'),
    ], string='Müşteri Tipi', default='sirket', tracking=True)
    musteri_id = fields.Many2one(
        'res.partner', 
        string='Müşteri', 
        required=True # Ürün mutlaka bir müşteriye ait olmalı diyorsak
    )
    musteri_ref_id = fields.Integer(
        related='musteri_id.id', 
        string='Müşteri Sistem ID', 
        readonly=True,
        store=True
    )
    musteri_adi = fields.Char(related='musteri_id.name', string='Müşteri Adı', readonly=True)

    @api.onchange('musteri_tipi')
    def _onchange_musteri_tipi(self):
        self.musteri_id = False
        if self.musteri_tipi == 'sahis':
            return {'domain': {'musteri_id': [('is_company', '=', False)]}}
        else:
            return {'domain': {'musteri_id': [('is_company', '=', True)]}}
    
    # Garanti Bilgileri
    garanti_baslama = fields.Date(string='Garanti Başlama Tarihi')
    garanti_suresi = fields.Integer(string='Garanti Süresi (Ay)', default=24)
    garanti_bitis = fields.Date(string='Garanti Bitiş Tarihi', compute='_compute_garanti_bitis', store=True)
    garanti_durumu = fields.Selection([
        ('yok', 'Garantisi Yok'),
        ('devam', 'Garantisi Devam Ediyor'),
        ('belirsiz', 'Belirsiz')
    ], compute='_compute_garanti_durumu')

    @api.depends('garanti_bitis')
    def _compute_garanti_durumu(self):
        today = date.today()
        for record in self:
            # Eğer garanti başlama tarihi girilmemiş veya garanti süresi 0/boş ise → 'yok'
            if not record.garanti_baslama or not record.garanti_bitis:
                record.garanti_durumu = 'yok'
            elif record.garanti_bitis < today:
                record.garanti_durumu = 'yok'
            else:
                record.garanti_durumu = 'devam'

    
    notes = fields.Text(string='Notlar')

    note_ids = fields.One2many('urun.notu', 'urun_id', string='Notlar')
    dokuman_ids = fields.One2many('urun.dokuman', 'urun_id', string='Dokümanlar')

    # 1. Gelecek Tarih Kontrolü (Kaydetme anında kesin engel)
    @api.constrains('garanti_baslama')
    def _check_garanti_baslama_date(self):
        for record in self:
            if record.garanti_baslama and record.garanti_baslama > date.today():
                raise ValidationError(("Garanti Başlama Tarihi bugünden ileri bir tarih olamaz!"))

    # 2. Garanti Bitiş Tarihi Hesaplama (Tam Ay Hesabı)
    @api.depends('garanti_baslama', 'garanti_suresi')
    def _compute_garanti_bitis(self):
        for record in self:
            if record.garanti_baslama and record.garanti_suresi:
                # relativedelta takvimdeki aya göre (28, 30 veya 31 gün) tam hesaplama yapar
                record.garanti_bitis = record.garanti_baslama + relativedelta(months=record.garanti_suresi)
            else:
                record.garanti_bitis = False

    # 3. Anlık Tarih Kontrolü (Tarih seçildiği anda uyarı verir ve siler)
    @api.onchange('garanti_baslama')
    def _onchange_garanti_baslama(self):
        if self.garanti_baslama and self.garanti_baslama > date.today():
            self.garanti_baslama = False  # 🔴 Geçersiz tarihi temizle
            return {
                'warning': {
                    'title': ("Geçersiz Tarih"),
                    'message': ("Garanti Başlama Tarihi bugünden ileri bir tarih olamaz.")
                }
            }

    # Ürün Kodu Otomatik Artış (URN0000001)
    def create(self, vals_list):
        if not isinstance(vals_list, list):
            vals_list = [vals_list]
        for vals in vals_list:
            if isinstance(vals, dict):
                if vals.get('name', 'Yeni') == 'Yeni':
                    vals['name'] = self.env['ir.sequence'].next_by_code('servis.urun.sequence') or 'Yeni'
        return super(ServisUrun, self).create(vals_list)
    
    

