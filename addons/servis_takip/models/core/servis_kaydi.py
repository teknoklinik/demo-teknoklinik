from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from datetime import date, datetime
import logging
from .servis_durum import SERVIS_DURUM_SELECTION, DURUM_RENK_MAP
from dateutil.relativedelta import relativedelta

_logger = logging.getLogger(__name__)

class ServisKaydi(models.Model):
    _name = 'servis.kaydi'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'barkod.etiketi.mixin']
    _description = 'Teknik Servis Onarım Kaydı'
    _rec_name = 'name' 

    # --- Kimlik ve Müşteri Bilgileri ---
    name = fields.Char(string='Referans No', required=True, readonly=True, default='Yeni', copy=False)
    musteri_tipi = fields.Selection([
        ('sahis', 'Şahıs'),
        ('sirket', 'Şirket'),
    ], string='Müşteri Tipi', default='sirket', tracking=True) 
    
    musteri_id = fields.Many2one(
        'res.partner',
        string='Müşteri',
        domain="[('is_company', '=', musteri_tipi == 'sirket')]",
        tracking=True
    )
    
    # --- Durum ve Görsel Yönetim ---
    state = fields.Selection(
        selection='_get_durum_listesi',
        string='Durumu',
        default='kayit_yapildi',
        required=True,
        tracking=True,
    )

    def _get_durum_listesi(self):
        """Koddaki 8 ana durum + Kullanıcının eklediği yeni durumlar"""
        selection = list(SERVIS_DURUM_SELECTION)
        # Veritabanındaki özel durumları çek (ID'yi key, Name'i value olarak ekle)
        ekstra_durumlar = self.env['servis.durum.tanimi'].sudo().search([])
        for durum in ekstra_durumlar:
            # Mevcut kodlarla karışmaması için ID'yi string olarak key yapıyoruz
            selection.append((str(durum.id), durum.name))
        return selection

    color = fields.Integer(string='Durum Rengi', compute='_compute_color', store=True)
    state_badge_css = fields.Char(string='Durum Badge CSS', compute='_compute_state_badge_css', store=True)
    etiket_ids = fields.Many2many('servis.etiket', string='Etiketler')
    
    kayit_etiketi = fields.Char(compute='_compute_kayit_gorsel_verileri')
    kayit_etiketi_renk = fields.Char(compute='_compute_kayit_gorsel_verileri')
    kayit_etiketi_icon = fields.Char(compute='_compute_kayit_gorsel_verileri')

    # --- Ürün Bilgileri ---
    urun_turu_id = fields.Many2one('urun.turu', string='Ürün Türü', tracking=True)
    urun_marka_id = fields.Many2one('urun.markasi', string='Ürün Markası', domain="[('tur_id', '=', urun_turu_id)]", tracking=True)
    urun_modeli_id = fields.Many2one('urun.modeli', string='Ürün Modeli', domain="[('tur_id', '=', urun_turu_id), ('marka_id', '=', urun_marka_id)]", tracking=True)
    seri_no = fields.Char(string='Seri Numarası', tracking=True)
    barkod_no = fields.Char(string='Barkod No', tracking=True)

    # --- İlişkili Satırlar (One2many) ---
    durum_satirlari = fields.One2many(
        'servis.durum.satiri', 
        'servis_kaydi_id', 
        string="Durum Satırı", 
        copy=False, # Kopyalama yapıldığında eski geçmişi alma
        default=lambda self: self._get_default_durum_satirlari() # Varsayılan satır ekle
    )
    servis_islem_satirlari = fields.One2many('servis.islem.satiri', 'servis_kaydi_id', string='Yapılan İşlem Satırları', copy=True)
    ariza_detay_ids = fields.One2many('servis.kaydi.ariza.detay', 'servis_kaydi_id', string='Detaylar')
    teknik_rapor_satirlari = fields.One2many('servis.kaydi.teknik.rapor.satir', 'servis_kaydi_id', string="Parça ve Hizmetler", copy=True)
    notlar_ids = fields.One2many('servis.kaydi.notlar', 'servis_kaydi_id', string='Notlar', copy=True)
    aksesuar_ids = fields.One2many('servis.kaydi.aksesuar', 'servis_kaydi_id', string='Aksesuarlar', copy=True)
    deger_okuma_ids = fields.One2many('servis.kaydi.deger.okuma', 'servis_kaydi_id', string='Değer Okuma', copy=True)
    dokuman_yukle_ids = fields.One2many('servis.kaydi.dokuman', 'servis_kaydi_id', string='Dokümanlar', copy=True)
    teknisyen_notu = fields.Text(string='Teknisyen Notu', help='Teknisyen tarafından yapılan işlemler ve notlar')
    rapor_parca_hizmet_ekle = fields.Boolean(string='Parça ve Hizmetleri Rapora Ekle', default=True, help='İşaretlenirse raporda parça ve hizmetler gösterilir')
    
    # --- Özel Notebook Alanları ---
    ozel_notebook_1_label = fields.Char(string='Özel 1 Label', compute='_compute_ozel_notebook_labels', store=True)
    ozel_notebook_1_gozuksun = fields.Boolean(compute='_compute_ozel_notebook_visibility', store=True)
    ozel_notebook_1_satiri_ids = fields.One2many(
        'servis.ozel.notebook.satiri',
        'servis_kaydi_id',
        string='Özel Notebook 1 Satırları',
        domain=[('notebook_type', '=', 'notebook_1')]
    )

    # --- Kargolar Notebook Alanı ---
    kargolar_satiri_ids = fields.One2many(
        'servis.ozel.notebook.satiri',
        'servis_kaydi_id',
        string='Kargolar Satırları',
        domain=[('notebook_type', '=', 'kargolar')]
    )

    # 6 Özel Alan Değerleri (Computed - Listede görüntülenecek)
    ozel_alan_1_degeri = fields.Text(string='Özel Alan 1', compute='_compute_ozel_alan_degerleri', store=True)
    ozel_alan_2_degeri = fields.Text(string='Özel Alan 2', compute='_compute_ozel_alan_degerleri', store=True)
    ozel_alan_3_degeri = fields.Text(string='Özel Alan 3', compute='_compute_ozel_alan_degerleri', store=True)
    ozel_alan_4_degeri = fields.Text(string='Özel Alan 4', compute='_compute_ozel_alan_degerleri', store=True)
    ozel_alan_5_degeri = fields.Text(string='Özel Alan 5', compute='_compute_ozel_alan_degerleri', store=True)
    ozel_alan_6_degeri = fields.Text(string='Özel Alan 6', compute='_compute_ozel_alan_degerleri', store=True)
    
    # --- Finansal Alanlar ---
    company_id = fields.Many2one('res.company', string='Şirket', default=lambda self: self.env.company)
    company_currency_id = fields.Many2one('res.currency', string='Para Birimi', compute='_compute_company_currency_id', store=True)
    vergi_haric_tutar = fields.Monetary(string='Vergi Hariç Tutar:', compute='_compute_toplamlar', store=True, currency_field='company_currency_id')
    toplam_vergi = fields.Monetary(string='Vergiler:', compute='_compute_toplamlar', store=True, currency_field='company_currency_id')
    genel_toplam = fields.Monetary(string='Toplam:', compute='_compute_toplamlar', store=True, currency_field='company_currency_id')

    # --- Garanti Bilgileri ---
    garanti_baslama = fields.Date(string="Garanti Başlama Tarihi")
    garanti_suresi = fields.Integer(string="Garanti Süresi (Ay)", default=24)
    garanti_bitis = fields.Date(string="Garanti Bitiş Tarihi", compute='_compute_garanti_bitis', store=True)
    garanti_durumu= fields.Selection([
        ('yok', 'Garantisi Yok'),
        ('devam', 'Garantisi Devam Ediyor'),
        ('belirsiz', 'Belirsiz')
    ], compute='_compute_garanti_durumu')
    
    # --- Barkod Etiketi Kontrolleri ---
    barkod_etiketi_acilabilir = fields.Boolean(
        string='Barkod Etiketi Açılabilir',
        compute='_compute_barkod_etiketi_acilabilir',
        store=False
    )

    # --- Müşteri İmzaları ---
    kabul_musteri_imzasi = fields.Binary(string='Kabul Müşteri İmzası', copy=False)
    teslim_musteri_imzasi = fields.Binary(string='Teslim Müşteri İmzası', copy=False)

    # --- Ayarlardan gelen değerler ---
    show_urun_parkina_aktar_button = fields.Boolean(
        string='Ürün Parkına Aktar Butonu Göster',
        compute='_compute_show_urun_parkina_aktar_button',
        store=False
    )

    @api.depends()
    def _compute_show_urun_parkina_aktar_button(self):
        """Ayarlardan ürün parkı kayıt politikasını kontrol et"""
        kayit_politikasi = self.env['ir.config_parameter'].sudo().get_param(
            'servis_takip.urun_parki_kayit_politikasi',
            default='kayit_et'
        )
        for record in self:
            # Eğer 'kayit_etme' ise butonu göster
            record.show_urun_parkina_aktar_button = (kayit_politikasi == 'kayit_etme')

    @api.depends()
    def _compute_ozel_notebook_labels(self):
        """Özelleştirme modelinden özel notebook etiketlerini al"""
        ozellestirme = self.env['servis.ozellestirme'].get_ozellestirme()
        for record in self:
            record.ozel_notebook_1_label = ozellestirme.ozel_notebook_1_adi or 'Özel 1'

    @api.depends()
    def _compute_ozel_notebook_visibility(self):
        """Özelleştirme modelinden özel notebook görünürlüğünü al"""
        ozellestirme = self.env['servis.ozellestirme'].get_ozellestirme()
        for record in self:
            record.ozel_notebook_1_gozuksun = ozellestirme.ozel_notebook_1_gozuksun

    @api.depends('ozel_notebook_1_satiri_ids')
    def _compute_ozel_alan_degerleri(self):
        """Her özel alan için değerleri işle (alanları tuple yaparak özet oluştur)"""
        for record in self:
            # Özelleştirme ayarlarını al
            ozellestirme = self.env['servis.ozellestirme'].get_ozellestirme()
            
            # Alan isimleri (listede görünen adlandırma)
            alan_adlari = {
                'alan1': ozellestirme.ozel_alan_1_liste_adi or 'Özel Alan 1',
                'alan2': ozellestirme.ozel_alan_2_liste_adi or 'Özel Alan 2',
                'alan3': ozellestirme.ozel_alan_3_liste_adi or 'Özel Alan 3',
                'alan4': ozellestirme.ozel_alan_4_liste_adi or 'Özel Alan 4',
                'alan5': ozellestirme.ozel_alan_5_liste_adi or 'Özel Alan 5',
                'alan6': ozellestirme.ozel_alan_6_liste_adi or 'Özel Alan 6',
            }
            
            # Notebook satırlarından değerleri topla
            nilai_dict = {'alan1': [], 'alan2': [], 'alan3': [], 'alan4': [], 'alan5': [], 'alan6': []}
            
            for satir in record.ozel_notebook_1_satiri_ids:
                if satir.kolon in nilai_dict and satir.aciklama:
                    nilai_dict[satir.kolon].append(satir.aciklama)
            
            # Compute fields'larını doldur (alan adı: değerler)
            record.ozel_alan_1_degeri = ', '.join(nilai_dict.get('alan1', [])) or ''
            record.ozel_alan_2_degeri = ', '.join(nilai_dict.get('alan2', [])) or ''
            record.ozel_alan_3_degeri = ', '.join(nilai_dict.get('alan3', [])) or ''
            record.ozel_alan_4_degeri = ', '.join(nilai_dict.get('alan4', [])) or ''
            record.ozel_alan_5_degeri = ', '.join(nilai_dict.get('alan5', [])) or ''
            record.ozel_alan_6_degeri = ', '.join(nilai_dict.get('alan6', [])) or ''

    @api.model
    def fields_get(self, allfields=None, attributes=None):
        """Özel alan sütun başlıklarını dinamik olarak güncelle"""
        result = super().fields_get(allfields, attributes)
        
        # Özelleştirme ayarlarını al
        ozellestirme = self.env['servis.ozellestirme'].get_ozellestirme()
        
        # Computed field'ların string property'sini dinamik olarak ayarla
        if 'ozel_alan_1_degeri' in result:
            result['ozel_alan_1_degeri']['string'] = ozellestirme.ozel_alan_1_liste_adi or 'Özel Alan 1'
        if 'ozel_alan_2_degeri' in result:
            result['ozel_alan_2_degeri']['string'] = ozellestirme.ozel_alan_2_liste_adi or 'Özel Alan 2'
        if 'ozel_alan_3_degeri' in result:
            result['ozel_alan_3_degeri']['string'] = ozellestirme.ozel_alan_3_liste_adi or 'Özel Alan 3'
        if 'ozel_alan_4_degeri' in result:
            result['ozel_alan_4_degeri']['string'] = ozellestirme.ozel_alan_4_liste_adi or 'Özel Alan 4'
        if 'ozel_alan_5_degeri' in result:
            result['ozel_alan_5_degeri']['string'] = ozellestirme.ozel_alan_5_liste_adi or 'Özel Alan 5'
        if 'ozel_alan_6_degeri' in result:
            result['ozel_alan_6_degeri']['string'] = ozellestirme.ozel_alan_6_liste_adi or 'Özel Alan 6'
        
        return result

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

    @api.depends('musteri_id', 'urun_turu_id', 'urun_marka_id', 'urun_modeli_id', 'seri_no', 'ariza_detay_ids.ariza_tanimi_id')
    def _compute_barkod_etiketi_acilabilir(self):
        """Barkod Etiketinin tüm gerekli alanlar dolu ise açılabilir"""
        for record in self:
            # 5 alanın kontrol edilmesi
            temel_alanlar_ok = bool(
                record.musteri_id and 
                record.urun_turu_id and 
                record.urun_marka_id and 
                record.urun_modeli_id and 
                record.seri_no
            )
            
            # En az bir arıza tanımının dolu olması
            ariza_ok = any(detay.ariza_tanimi_id for detay in record.ariza_detay_ids)
            
            record.barkod_etiketi_acilabilir = temel_alanlar_ok and ariza_ok

    # 1. Gelecek Tarih Kontrolü (Hata Fırlatır)
    @api.constrains('garanti_baslama')
    def _check_garanti_baslama_date(self):
        for record in self:
            if record.garanti_baslama and record.garanti_baslama > date.today():
                raise ValidationError(_("Garanti Başlama Tarihi bugünden ileri bir tarih olamaz!"))

    # 2. Garanti Bitiş Tarihi Hesaplama (Daha doğru ay hesabı ile)
    @api.depends('garanti_baslama', 'garanti_suresi')
    def _compute_garanti_bitis(self):
        for record in self:
            if record.garanti_baslama and record.garanti_suresi:
                # relativedelta kullanarak takvime göre tam ay ekler
                record.garanti_bitis = record.garanti_baslama + relativedelta(months=record.garanti_suresi)
            else:
                record.garanti_bitis = False
    
    @api.onchange('garanti_baslama')
    def _onchange_garanti_baslama(self):
        if self.garanti_baslama and self.garanti_baslama > date.today():
            self.garanti_baslama = False  # 🔴 Alanı temizle
            return {
                'warning': {
                    'title': _("Geçersiz Tarih"),
                    'message': _("Garanti Başlama Tarihi bugünden ileri bir tarih olamaz.")
                }
            }

    # --- Tarihler ve Süreler ---
    kayit_tarihi = fields.Datetime(string='Ürün Giriş Tarihi', required=True, default=fields.Datetime.now, readonly=True, copy=False)
    teslim_tarihi = fields.Datetime(string='Teslim Edildiği Tarih', compute='_compute_teslim_tarihi', store=True, readonly=True)
    teslim_edildi_by_id = fields.Many2one('res.users', string='Teslim Eden Kullanıcı', readonly=True, copy=False)
    serviste_gecen_sure = fields.Char(string='Serviste Geçen Süre', compute='_compute_serviste_gecen_sure')
    sure_asimi_var = fields.Boolean(compute="_compute_sure_asimi", store=False)
    sure_asimi_mesaji = fields.Char(string='Süre Aşımı Mesajı', compute='_compute_sure_asimi_mesaji', store=False)

    def _compute_sure_asimi(self):
        # Ayarlardan servis süre aşımı limitini al (default: 21 gün)
        sure_asimi_limiti = int(self.env['ir.config_parameter'].sudo().get_param(
            'servis_takip.servis_sure_asimi_limiti',
            default='21'
        ))
        
        for rec in self:
            if rec.kayit_tarihi and rec.state not in ['teslim_edildi', 'iptal']:
                # Giriş tarihinden bugüne ne kadar zaman geçtiğini hesapla
                fark = datetime.now() - rec.kayit_tarihi
                # Eğer geçen süre ayarlanan limitten büyükse True dön
                rec.sure_asimi_var = fark.days >= sure_asimi_limiti
            else:
                rec.sure_asimi_var = False

    @api.depends('sure_asimi_var')
    def _compute_sure_asimi_mesaji(self):
        """Ayarlardan gelen limite göre dinamik mesaj oluştur"""
        sure_asimi_limiti = int(self.env['ir.config_parameter'].sudo().get_param(
            'servis_takip.servis_sure_asimi_limiti',
            default='21'
        ))
        
        for rec in self:
            if rec.sure_asimi_var:
                rec.sure_asimi_mesaji = f"{sure_asimi_limiti} gün limitini aştınız!"
            else:
                rec.sure_asimi_mesaji = ""
    
    servis_form_kapali_mi = fields.Selection([
        ('acik', 'Açık'),
        ('kapali', 'Kapalı')
    ], string="Form Kapalı Mı?", compute="_compute_form_kapali_mi", store=True)    

    @api.depends('state')
    def _compute_form_kapali_mi(self):
        for rec in self:
            # ÖNEMLİ: 'teslim_edildi' ve 'iptal' senin sistemindeki teknik isimler olmalı
            if rec.state in ['teslim_edildi', 'iptal']:
                rec.servis_form_kapali_mi = 'kapali'
            else:
                rec.servis_form_kapali_mi = 'acik'

    # --- Diğer Alanlar ---
    islem_tipi_id = fields.Many2one('servis.islem.tipi', string='İşlem Tipi', domain="[('aktif', '=', True)]", tracking=True)
    tablo_duzenle = fields.Boolean(string="Tablo Düzenlenebilir", default=False)
    rapor_olusturuldu = fields.Boolean(string="Rapor Oluşturuldu", default=False, copy=False)

    # --- Form Düzenle ---
    formu_duzenle = fields.Boolean(string="Formu Düzenle", default=False)
    def action_toggle_form_edit(self):
        for record in self:
            # Eğer düzenleme modundaysa ve butona basıldıysa (Tamamla aşaması)
            if record.formu_duzenle:
                record.formu_duzenle = False
                # Kaydet ve sayfayı yenile (F5 etkisi)
                return {
                    'type': 'ir.actions.client',
                    'tag': 'reload',
                }
            else:
                # Düzenleme modunu aç (Düzenle aşaması)
                record.formu_duzenle = True
        return True
    
    def action_baslat(self):
        """Sayfayı yenile - durum tablosu görünür olacak"""
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }
    
    # --- Compute Metotları ---
    @api.depends('state')
    def _compute_kayit_gorsel_verileri(self):
        for rec in self:
            if rec.state in ['teslim_edildi', 'iptal']:
                rec.kayit_etiketi = 'KAPALI KAYIT'
                rec.kayit_etiketi_renk = '#dc3545'
                rec.kayit_etiketi_icon = 'fa-lock'
            else:
                rec.kayit_etiketi = 'AÇIK KAYIT'
                rec.kayit_etiketi_renk = '#28a745'
                rec.kayit_etiketi_icon = 'fa-unlock-alt'

    @api.depends('state')
    def _compute_color(self):
        for record in self:
            # Önce koddaki renk haritasına bak
            color = DURUM_RENK_MAP.get(record.state, 0)
            if not color and record.state:
                # Eğer koddaki listede yoksa, veritabanındaki tanımdan rengi çek
                try:
                    # Eğer state bir ID ise (ekstra durumdur)
                    durum_id = int(record.state)
                    ekstra = self.env['servis.durum.tanimi'].sudo().browse(durum_id)
                    color = ekstra.color
                except:
                    color = 0
            record.color = color

    # Odoo renk indekslerinin hex değerleri
    COLOR_HEX_MAP = {
        1: '#dc3545',   # Kırmızı
        2: '#fd7e14',   # Turuncu
        3: '#ffc107',   # Sarı
        4: '#17a2b8',   # Açık Mavi
        5: '#6f42c1',   # Mor
        6: '#e83e8c',   # Pembe
        7: '#007bff',   # Mavi
        8: '#003d82',   # Koyu Mavi
        9: '#28a745',   # Yeşil
        10: '#20c997',  # Açık Yeşil
        11: '#6c757d',  # Gri
        0: '#6c757d',   # Varsayılan Gri
    }

    @api.depends('color')
    def _compute_state_badge_css(self):
        """Durum rengine göre badge için CSS sınıfı oluşturur"""
        for record in self:
            # Renk indeksine göre hex değeri al
            hex_color = self.COLOR_HEX_MAP.get(record.color, self.COLOR_HEX_MAP[0])
            # Badge için inline style oluştur
            record.state_badge_css = f"background-color: {hex_color} !important; color: white !important;"

    @api.depends('kayit_tarihi', 'state', 'teslim_tarihi')
    def _compute_serviste_gecen_sure(self):
        now = fields.Datetime.now()
        for record in self:
            if record.kayit_tarihi:
                end = record.teslim_tarihi if record.state in ('teslim_edildi', 'iptal') and record.teslim_tarihi else now
                delta = end - record.kayit_tarihi
                days = delta.days
                hours = delta.seconds // 3600
                minutes = (delta.seconds % 3600) // 60
                res = []
                if days > 0: res.append(f"{days} Gün")
                if hours > 0: res.append(f"{hours} Saat")
                if minutes > 0: res.append(f"{minutes} Dakika")
                record.serviste_gecen_sure = " ".join(res) if res else "0 Dakika"
            else:
                record.serviste_gecen_sure = "0 Dakika"

    @api.depends('state', 'durum_satirlari.tarih') 
    def _compute_teslim_tarihi(self): 
        for record in self: 
            record.teslim_tarihi = False 
            record.teslim_edildi_by_id = False
            if record.state in ('teslim_edildi', 'iptal'): 
                satir = record.durum_satirlari.filtered(lambda s: s.state == record.state and s.tarih) 
                if satir:
                    last = satir.sorted(key=lambda s: s.tarih)[-1] 
                    record.teslim_tarihi = last.tarih
                    if last.personel_id and last.personel_id.user_id:
                        record.teslim_edildi_by_id = last.personel_id.user_id.id

    @api.depends(
            'teknik_rapor_satirlari.ornek_ara_toplam', 
            'teknik_rapor_satirlari.ornek_vergiler', 
            'teknik_rapor_satirlari.ornek_miktar',
            'teknik_rapor_satirlari.ornek_birim_fiyat')
    def _compute_toplamlar(self):
        for record in self:
            v_haric = 0.0
            v_toplam = 0.0
            for line in record.teknik_rapor_satirlari:
                # Odoo'nun standart vergi hesaplama motoru
                taxes = line.ornek_vergiler.compute_all(
                    line.ornek_birim_fiyat, 
                    currency=record.company_currency_id, 
                    quantity=line.ornek_miktar, 
                    product=line.ornek_urun_id, 
                    partner=record.musteri_id
                )
                v_haric += taxes['total_excluded']
                v_toplam += (taxes['total_included'] - taxes['total_excluded'])
            
            record.vergi_haric_tutar = v_haric
            record.toplam_vergi = v_toplam
            record.genel_toplam = v_haric + v_toplam

    @api.depends('company_id')
    def _compute_company_currency_id(self):
        for record in self:
            record.company_currency_id = record.company_id.currency_id

    currency_symbol = fields.Char(string='Para Birimi Sembolü', compute='_compute_currency_symbol', store=True)

    @api.depends('company_currency_id')
    def _compute_currency_symbol(self):
        for record in self:
            record.currency_symbol = record.company_currency_id.symbol if record.company_currency_id else '₺'

    # --- Yardımcı Metotlar ---
    def _create_status_line(self, durum_kodu, aciklama, personel_id=None):
        self.ensure_one()
        p_id = personel_id if personel_id is not None else self.env.user.employee_ids[:1].id
        self.env['servis.durum.satiri'].create({
            'servis_kaydi_id': self.id,
            'state': durum_kodu, 
            'personel_id': p_id,
            'aciklama': aciklama,
        })
        durum_adi = dict(SERVIS_DURUM_SELECTION).get(durum_kodu, durum_kodu)
        self.message_post(body=_(f"Durum değişti: **{durum_adi}**"))
        
    def _create_islem_satiri(self, islem_tipi_id, aciklama):
        self.env['servis.islem.satiri'].create({
            'servis_kaydi_id': self.id,
            'islem_tipi_id': islem_tipi_id,
            'aciklama': aciklama,
            'personel_id': self.env.user.id,
            'tarih': fields.Datetime.now(),
        })

    def _get_default_durum_satirlari(self):
        """Yeni kayıt dendiği anda 'Kaydı Yapıldı' satırını ekranda hazır getirir."""
        p_id = self.env.user.employee_id.id if self.env.user.employee_id else False        
        return [(0, 0, {
            'state': 'kayit_yapildi', # DURUM modelindeki Selection key'i ile birebir aynı olmalı
            'tarih': fields.Datetime.now(),
            'aciklama': 'Servis kaydı oluşturuldu.',
            'personel_id': p_id,
        })]
    
    # --- CRUD ---
    @api.model_create_multi
    def create(self, vals_list):
        # skip_required_check varsa kontrol yapma
        if not self.env.context.get('skip_required_check'):
            for vals in vals_list:
                # Eğer hiçbir required alan dolduysa kontrol et
                # (Boş kayıt oluşturuluyorsa kontrol etme - button'dan oluşturulabilir)
                has_any_required = (
                    vals.get('musteri_id') or vals.get('urun_turu_id') or 
                    vals.get('urun_marka_id') or vals.get('urun_modeli_id') or 
                    vals.get('seri_no') or vals.get('ariza_detay_ids')
                )
                
                if has_any_required:
                    eksikler = []
                    if not vals.get('musteri_id'):
                        eksikler.append("Müşteri")
                    if not vals.get('urun_turu_id'):
                        eksikler.append("Ürün Türü")
                    if not vals.get('urun_marka_id'):
                        eksikler.append("Ürün Markası")
                    if not vals.get('urun_modeli_id'):
                        eksikler.append("Ürün Modeli")
                    if not vals.get('seri_no'):
                        eksikler.append("Seri No")
                    if not vals.get('ariza_detay_ids'):
                        eksikler.append("En Az Bir Arıza Tipi")
                    
                    if eksikler:
                        from odoo.exceptions import UserError
                        raise UserError(
                            _("Aşağıdaki alanlar doldurulmadan devam edemezsiniz:\n• %s")
                            % "\n• ".join(eksikler)
                        )
        
        for vals in vals_list:
            # 1. İsim atama
            if vals.get('name', 'Yeni') == 'Yeni':
                vals['name'] = self.env['ir.sequence'].next_by_code('servis.kaydi.referans') or 'Yeni'
            
            # 2. Kritik Kontrol: Eğer durum_satirlari vals içinde hiç yoksa veya boşsa
            # (Sizin durumunuzda başta dolu gelip sonra boşalıyorsa vals içinden düşüyor demektir)
            if not vals.get('durum_satirlari'):
                p_id = self.env.user.employee_id.id if self.env.user.employee_id else False
                vals['durum_satirlari'] = [(0, 0, {
                    'state': 'kayit_yapildi',
                    'tarih': fields.Datetime.now(),
                    'aciklama': 'Servis kaydı oluşturuldu.',
                    'personel_id': p_id,
                })]
                
        # Ana kaydı oluştur
        records = super(ServisKaydi, self).create(vals_list)
        
        # 3. İKİNCİ GÜVENLİK KATI: Eğer üstteki işe yaramazsa (Veritabanına manuel yaz)
        for rec in records:
            if not rec.durum_satirlari:
                self.env['servis.durum.satiri'].create({
                    'servis_kaydi_id': rec.id,
                    'state': 'kayit_yapildi',
                    'aciklama': 'Servis kaydı oluşturuldu (Sistem Tarafından).',
                    'personel_id': self.env.user.employee_id.id if self.env.user.employee_id else False,
                })

        # 3. Ayar Kontrolü: Kayıt politikasına bak
        politikasi = self.env['ir.config_parameter'].sudo().get_param('servis_takip.urun_parki_kayit_politikasi', default='kayit_et')

        if politikasi == 'kayit_et':
            for rec in records:
                # DÖRT KONTROL: Tür, Marka, Model ve Seri No dolu mu?
                if rec.seri_no and rec.urun_turu_id and rec.urun_marka_id and rec.urun_modeli_id:
                    
                    # Ürün Parkı'nda bu dördünün birden eşleştiği bir kayıt var mı?
                    mevcut = self.env['servis.urun'].search([
                        ('serial_no', '=', rec.seri_no),
                        ('tur_id', '=', rec.urun_turu_id.id),
                        ('marka_id', '=', rec.urun_marka_id.id),
                        ('model_id', '=', rec.urun_modeli_id.id)
                    ], limit=1)

                    if not mevcut:
                        # Ürün Parkı'ndaki sequence kodunu kullanarak isim al
                        # Not: 'servis.urun.sequence' kısmını kendi sequence kodunla değiştir
                        urun_kodu = self.env['ir.sequence'].next_by_code('servis.urun.sequence') or 'YENI-URUN'
                        
                        self.env['servis.urun'].sudo().create({
                            'name': urun_kodu, # Otomatik artan ürün kodu
                            'musteri_id': rec.musteri_id.id,
                            'tur_id': rec.urun_turu_id.id,
                            'marka_id': rec.urun_marka_id.id,
                            'model_id': rec.urun_modeli_id.id,
                            'serial_no': rec.seri_no,
                            'barcode': rec.barkod_no,
                            'garanti_baslama': rec.garanti_baslama,
                            'garanti_suresi': rec.garanti_suresi,
                        })
                
        return records
    
    def write(self, vals):
        # Eğer satırlarda bir oynama varsa tabloyu kilitle
        if 'servis_islem_satirlari' in vals:
            vals['tablo_duzenle'] = False

        # Durum değiştiğinde otomatik işlem satırı oluşturma
        if 'state' in vals:
            for record in self:
                if vals['state'] in ('inceleme', 'islemde') and record.islem_tipi_id:
                    record._create_islem_satiri(
                        record.islem_tipi_id.id,
                        _('Yeni iş akışı başladı.')
                    )

        res = super(ServisKaydi, self).write(vals)

        # ⛔️ Wizard / buton / teknik write'ları tamamen atla
        if self.env.context.get('skip_required_check'):
            return res

        # ⛔️ Boş write (autosave, button click) → kontrol etme
        if not vals:
            return res

        # ⛔️ Required alanlarla alakası yoksa kontrol etme
        kontrol_alanlari = {
            'musteri_id',
            'urun_turu_id',
            'urun_marka_id',
            'urun_modeli_id',
            'seri_no',
        }

        if kontrol_alanlari.isdisjoint(vals.keys()):
            return res
        
        # ⛔️ Eğer başka alanlar da dolu değilse (onchange sırasında) kontrol etme
        # (button'a basıldığında geçici save olup required alanlar boş kalabilir)
        has_required = False
        for rec in self:
            if (rec.musteri_id and rec.urun_turu_id and rec.urun_marka_id 
                and rec.urun_modeli_id and rec.seri_no):
                has_required = True
                break
        
        if not has_required:
            return res

        # ✅ SADECE REQUIRED ALANLAR DEĞİŞİYORSA KONTROL ET
        self._check_zorunlu_alanlar()

        return res

    # --- Action Butonları ---
    def action_tabloyu_ac(self): self.tablo_duzenle = True
    def action_tabloyu_kilitle(self): self.tablo_duzenle = False

    # --- Kabul Formu için Bağlantı ---

    def action_kabul_formu_pdf(self):
        self.ensure_one()

        # Formun var olup olmadığını kontrol et
        formu = self.env['kabul.formu'].search([('servis_id', '=', self.id)], limit=1)
        
        # Form yoksa oluştur
        if not formu:
            kabul_no = self.env['ir.sequence'].next_by_code('kabul.formu.sequence') or f'KBL-{self.id}'
            formu = self.env['kabul.formu'].create({
                'name': kabul_no,
                'servis_id': self.id,
                'musteri_id': self.musteri_id.id if self.musteri_id else False,
            })
        
        # Formu yeni sekmede aç
        return {
            'type': 'ir.actions.act_url',
            'url': f'/report/pdf/servis_takip.report_kabul_formu_template/{self.id}',
            'target': 'new',
        }

    # --- Teslim Formu için Bağlantı ---

    def action_teslim_formu_pdf(self):
        self.ensure_one()

        # --- 2. YÖNTEM KONTROLÜ BAŞLANGIÇ ---
        # Eğer 'Parça ve Hizmetleri Forma Ekle' seçili DEĞİLSE
        if not self.rapor_parca_hizmet_ekle:
            # Teknisyen notu boş mu veya sadece boşluk mu?
            if not self.teknisyen_notu or not self.teknisyen_notu.strip():
                raise UserError(
                    "Teslim Formu Oluşturulamadı!\n\n"
                    "Parça ve Hizmetleri Forma Ekle seçeneği işaretli değil. "
                    "Bu durumda müşteriye yapılan işlemler hakkında bilgi vermek için "
                    "'Teknisyen Notu' alanını doldurmanız gerekmektedir."
                )
        # --- 2. YÖNTEM KONTROLÜ BİTİŞ ---

        # Formun var olup olmadığını kontrol et
        formu = self.env['teslim.formu'].search([('servis_id', '=', self.id)], limit=1)
        
        # Form yoksa oluştur
        if not formu:
            teslim_no = self.env['ir.sequence'].next_by_code('teslim.formu.sequence') or f'TSL-{self.id}'
            formu = self.env['teslim.formu'].create({
                'name': teslim_no,
                'servis_id': self.id,
                'musteri_id': self.musteri_id.id if self.musteri_id else False,
            })
        
        # Formu yeni sekmede aç
        return {
            'type': 'ir.actions.act_url',
            'url': f'/report/pdf/servis_takip.report_teslim_formu_template/{self.id}',
            'target': 'new',
        }
    
    def action_open_formu_gonder_wizard(self):
        """Form gönderme wizard'ını aç"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'servis.formu.gonder.wizard',
            'view_mode': 'form',
            'view_type': 'form',
            'target': 'new',
            'context': {
                'default_servis_kaydi_id': self.id,
            },
        }
    
    def copy(self, default=None):
        # Eğer default sözlüğü gelmemişse boş bir sözlük oluştur
        default = dict(default or {})
        
        # Notebook (One2many) alanlarının kopyalanmasını engellemek için
        # default sözlüğüne boşaltma komutlarını ekliyoruz.
        # Bu alanlar artık 'copy=True' olsa bile kopyalanmayacak.
        default.update({
            'durum_satirlari': [(5, 0, 0)],
            'servis_islem_satirlari': [(5, 0, 0)],
            'ariza_detay_ids': [(5, 0, 0)],
            'teknik_rapor_satirlari': [(5, 0, 0)],
            'notlar_ids': [(5, 0, 0)],
            'dokuman_yukle_ids': [(5, 0, 0)],
        })
        
        return super(ServisKaydi, self).copy(default)
    
    @api.model
    def get_views(self, views, options=None):
        res = super().get_views(views, options=options)
        if 'form' in res['views']:
            allowed_states = ['islem_tamamlandi', 'teslim_edildi']
        return res
    
    def action_copy_records(self):
        for record in self:
            new_name = self.env['ir.sequence'].next_by_code('servis.kaydi.referans') or 'Yeni'
            record.copy(default={
                'name': new_name,
                'kayit_tarihi': fields.Datetime.now(),
                'state': 'kayit_yapildi', 
            })
        return {'type': 'ir.actions.client', 'tag': 'reload'}
    
    def action_urun_aktar_wizard(self):
        self.ensure_one()
        return {
            'name': 'Ürün Parkı',
            'type': 'ir.actions.act_window',
            'res_model': 'servis.urun.aktar.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'skip_required_check': True},
        }
    
    def _check_zorunlu_alanlar(self):
        for rec in self:
            eksikler = []

            if not rec.musteri_id:
                eksikler.append("Müşteri")

            if not rec.urun_turu_id:
                eksikler.append("Ürün Türü")

            if not rec.urun_marka_id:
                eksikler.append("Ürün Markası")

            if not rec.urun_modeli_id:
                eksikler.append("Ürün Modeli")

            if not rec.seri_no:
                eksikler.append("Seri No")    

            if eksikler:
                raise UserError(
                    _("Aşağıdaki alanlar doldurulmadan devam edemezsiniz:\n• %s")
                    % "\n• ".join(eksikler)
                )
            
    @api.onchange('seri_no', 'urun_turu_id', 'urun_marka_id', 'urun_modeli_id')
    def _onchange_check_urun_parki(self):
        """
        Ürün Parkı'nı kontrol eder:
        1. Farklı müşteri ise: Uyarı ver ve seri noyu sil.
        2. Aynı müşteri ise: Barkod ve Garanti bilgilerini otomatik doldur.
        """
        # Kontrol için en az Seri No ve Ürün Türü dolu olmalı
        if not self.seri_no or not self.urun_turu_id:
            return

        # Ürün Parkı'nda (servis.urun) ara
        domain = [
            ('serial_no', '=', self.seri_no),
            ('tur_id', '=', self.urun_turu_id.id)
        ]
        if self.urun_marka_id:
            domain.append(('marka_id', '=', self.urun_marka_id.id))
        if self.urun_modeli_id:
            domain.append(('model_id', '=', self.urun_modeli_id.id))

        mevcut_urun = self.env['servis.urun'].search(domain, limit=1)

        if mevcut_urun:
            # DURUM 1: Başka Müşteriye Ait (KESİN ENGEL)
            if mevcut_urun.musteri_id.id != self.musteri_id.id:
                musteri_adi = mevcut_urun.musteri_id.name
                temp_seri = self.seri_no
                self.seri_no = False
                self.urun_turu_id = False
                self.urun_marka_id = False
                self.urun_modeli_id = False
                self.barkod_no = False
                self.musteri_id = False 
                return {
                    'warning': {
                        'title': "Kritik Uyarı: Farklı Müşteri!",
                        'message': f"{temp_seri} seri numaralı ürün sistemde zaten '{musteri_adi}' adına kayıtlıdır. "
                                   f"Başka bir müşteri üzerine kayıt yapılamaz.",
                    }
                }

            # DURUM 2: Aynı Müşteri (OTOMATİK DOLDUR)
            else:
                # Bilgileri mevcut_urun kaydından çekip servis formuna yazıyoruz
                self.barkod_no = mevcut_urun.barcode
                self.garanti_baslama = mevcut_urun.garanti_baslama
                self.garanti_suresi = mevcut_urun.garanti_suresi
                
                # Kullanıcıya bilgi vermek istersen bir alt mesaj (warning) dönebilirsin
                # İstemezsen return kısmını tamamen silebilirsin, bilgiler yine de dolar.
                return {
                    'warning': {
                        'title': "Ürün Parkı Bilgileri Aktarıldı",
                        'message': "Bu ürün Ürün Parkı'nda kayıtlı bulundu. Barkod ve Garanti bilgileri otomatik olarak dolduruldu.",
                    }
                }
    
    # Fatura ve Teklif ID'lerini saklamak için alanlar
    fatura_id = fields.Many2one('account.move', string="Bağlı Fatura", copy=False)
    teklif_id = fields.Many2one('sale.order', string="Bağlı Teklif", copy=False)

    def action_buton_teklif(self):
        self.ensure_one()
        if not self.musteri_id:
            raise UserError("Lütfen önce bir müşteri seçin!")
        
        # Satır hazırlama
        line_values = []
        for line in self.teknik_rapor_satirlari:
            line_values.append((0, 0, {
                'product_id': line.ornek_urun_id.id,
                'name': line.ornek_aciklama or line.ornek_urun_id.display_name,
                'product_uom_qty': line.ornek_miktar,
                'price_unit': line.ornek_birim_fiyat,
            }))

        # Hata aldığın yer burasıydı, şimdi daha güvenli sorguluyoruz
        existing_id = False
        if self.teklif_id:
            try:
                # Odoo'ya zorla "bu bir sale.order'dır" diyoruz
                existing_id = self.env['sale.order'].browse(self.teklif_id.id).exists()
            except:
                existing_id = False

        if existing_id:
            if existing_id.state not in ['draft', 'sent']:
                raise UserError("Onaylanmış bir teklifi güncelleyemezsiniz. Lütfen teklifi taslağa çekin.")
            # GÜNCELLE
            existing_id.order_line.unlink()
            existing_id.write({'order_line': line_values})
            res_id = existing_id.id
        else:
            # YENİ OLUŞTUR
            teklif = self.env['sale.order'].create({
                'partner_id': self.musteri_id.id,
                'order_line': line_values,
                'origin': self.name,
            })
            # Veritabanına zorla yazıyoruz
            self.write({'teklif_id': teklif.id})
            self.env.cr.commit() # Veritabanı işlemini hemen onayla
            res_id = teklif.id

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'sale.order',
            'res_id': res_id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_buton_fatura(self):
        self.ensure_one()
        if not self.musteri_id:
            raise UserError("Lütfen önce bir müşteri seçin!")

        # Satır hazırlama
        line_values = []
        for line in self.teknik_rapor_satirlari:
            line_values.append((0, 0, {
                'product_id': line.ornek_urun_id.id,
                'name': line.ornek_aciklama or line.ornek_urun_id.display_name,
                'quantity': line.ornek_miktar,
                'price_unit': line.ornek_birim_fiyat,
                'tax_ids': [(6, 0, line.ornek_vergiler.ids)],
            }))

        existing_invoice = False
        if self.fatura_id:
            try:
                existing_invoice = self.env['account.move'].browse(self.fatura_id.id).exists()
            except:
                existing_invoice = False

        is_new_invoice = False
        if existing_invoice:
            if existing_invoice.state != 'draft':
                raise UserError("Onaylanmış bir faturayı güncelleyemezsiniz. Lütfen faturayı taslağa çekin.")
            
            existing_invoice.invoice_line_ids.unlink()
            existing_invoice.write({'invoice_line_ids': line_values})
            res_id = existing_invoice.id
        else:
            fatura = self.env['account.move'].create({
                'move_type': 'out_invoice',
                'partner_id': self.musteri_id.id,
                'invoice_line_ids': line_values,
                'invoice_origin': self.name,
            })
            self.write({'fatura_id': fatura.id})
            self.env.cr.commit() 
            res_id = fatura.id
            is_new_invoice = True

        # Fatura oluştururken ürün parkı kayıt politikasını kontrol et
        if is_new_invoice:
            fatura_kayit_politikasi = self.env['ir.config_parameter'].sudo().get_param(
                'servis_takip.fatura_urun_parki_kayit_politikasi',
                default='kayit_etme'
            )
            
            # Eğer politika 'kayit_et' ise otomatik ürün parkına kayıt yap
            if fatura_kayit_politikasi == 'kayit_et':
                try:
                    # Gerekli alanlar var mı kontrol et
                    if (self.seri_no and self.urun_turu_id and 
                        self.urun_marka_id and self.urun_modeli_id):
                        # Fatura tarihi varsa onu gönder
                        fatura_ref = self.env['account.move'].browse(res_id)
                        garanti_baslama_tarihi = fatura_ref.invoice_date if fatura_ref.invoice_date else fields.Date.today()
                        self._auto_urun_parkina_kayit(garanti_baslama_tarihi)
                except Exception as e:
                    # Hata oluşsa bile fatura oluşturulmuş olsun, sadece log'la
                    _logger.warning(f"Fatura ürün parkı otomatik kaydı yapılamadı: {str(e)}")

        # YARDIMCI FONKSİYON YERİNE DOĞRUDAN RETURN (Hata veren yer burasıydı)
        return {
            'name': 'Müşteri Faturası',
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'res_id': res_id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_imza_al_kabul(self):
        """Kabul formu için müşteri imzası al"""
        self.ensure_one()
        
        # Kabul formunun var olup olmadığını kontrol et, yoksa oluştur
        kabul_formu = self.env['kabul.formu'].search([
            ('servis_id', '=', self.id)
        ], limit=1)
        
        if not kabul_formu:
            kabul_no = self.env['ir.sequence'].next_by_code('kabul.formu.sequence') or f'KBL-{self.id}'
            kabul_formu = self.env['kabul.formu'].create({
                'name': kabul_no,
                'servis_id': self.id,
                'musteri_id': self.musteri_id.id if self.musteri_id else False,
            })
        
        return {
            'type': 'ir.actions.act_window',
            'name': 'Müşteri İmzası - Kabul Formu',
            'res_model': 'imza.al.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_servis_kaydi_id': self.id,
                'default_formu_tipi': 'kabul',
            }
        }

    def action_imza_al_teslim(self):
        """Teslim formu için müşteri imzası al"""
        self.ensure_one()
        
        # Teslim formunun var olup olmadığını kontrol et, yoksa oluştur
        teslim_formu = self.env['teslim.formu'].search([
            ('servis_id', '=', self.id)
        ], limit=1)
        
        if not teslim_formu:
            teslim_no = self.env['ir.sequence'].next_by_code('teslim.formu.sequence') or f'TSL-{self.id}'
            teslim_formu = self.env['teslim.formu'].create({
                'name': teslim_no,
                'servis_id': self.id,
                'musteri_id': self.musteri_id.id if self.musteri_id else False,
            })
        
        return {
            'type': 'ir.actions.act_window',
            'name': 'Müşteri İmzası - Teslim Formu',
            'res_model': 'imza.al.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_servis_kaydi_id': self.id,
                'default_formu_tipi': 'teslim',
            }
        }

    def action_urun_parkina_aktar(self):
        """Ürün bilgilerini ürün parkına aktar veya kontrol et"""
        self.ensure_one()
        
        # Gerekli ürün bilgilerinin tamamlandığını kontrol et
        if not all([self.urun_turu_id, self.urun_marka_id, self.urun_modeli_id, self.seri_no]):
            raise UserError(_('Ürün parkına aktar işlemi için lütfen Ürün Türü, Marka, Model ve Seri No bilgilerini doldurunuz.'))
        
        # Ürün parkında arama yap
        urun_parki = self.env['servis.urun'].search([
            ('tur_id', '=', self.urun_turu_id.id),
            ('marka_id', '=', self.urun_marka_id.id),
            ('model_id', '=', self.urun_modeli_id.id),
            ('serial_no', '=', self.seri_no),
        ], limit=1)
        
        if urun_parki:
            # Ürün parkında kayıtlı - müşteri kontrolü yap
            if urun_parki.musteri_id and urun_parki.musteri_id.id != self.musteri_id.id:
                raise UserError(_(
                    f"Bu ürün başka bir müşteriye kayıtlı!\n\n"
                    f"Kayıtlı Müşteri: {urun_parki.musteri_id.name}\n"
                    f"Mevcut Müşteri: {self.musteri_id.name}\n\n"
                    f"Lütfen ürün parkında başka müşteri için kayıtlı bilgisini kontrol edin."
                ))
            elif urun_parki.musteri_id and urun_parki.musteri_id.id == self.musteri_id.id:
                # Aynı müşteri için zaten kayıtlı
                raise UserError(_(
                    f"Bu ürün ürün parkında zaten kayıtlı!\n\n"
                    f"Ürün Parkı ID: {urun_parki.name}\n"
                    f"Müşteri: {urun_parki.musteri_id.name}\n"
                    f"Seri No: {urun_parki.serial_no}"
                ))
            else:
                # Ürün parkında kayıtlı ancak müşteri atanmamış
                urun_parki.write({'musteri_id': self.musteri_id.id})
                raise UserError(_(
                    f"Ürün parkında zaten var! Müşteri bilgisi güncellendi.\n\n"
                    f"Ürün Parkı ID: {urun_parki.name}"
                ))
        else:
            # Ürün parkında yok - yeni kayıt oluştur
            yeni_urun = self.env['servis.urun'].create({
                'tur_id': self.urun_turu_id.id,
                'marka_id': self.urun_marka_id.id,
                'model_id': self.urun_modeli_id.id,
                'serial_no': self.seri_no,
                'musteri_id': self.musteri_id.id,
                'garanti_baslama': self.garanti_baslama if self.garanti_baslama else fields.Date.today(),
            })
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Başarılı'),
                    'message': _(f'Ürün parkına başarıyla eklendi!\n\nÜrün Parkı ID: {yeni_urun.name}'),
                    'type': 'success',
                    'sticky': False,
                }
            }

    def _auto_urun_parkina_kayit(self, garanti_baslama_tarihi=None):
        """Ürün bilgilerini otomatik olarak ürün parkına kayıt et (fatura politikası için)"""
        self.ensure_one()
        
        # Gerekli ürün bilgilerinin tamamlandığını kontrol et
        if not all([self.urun_turu_id, self.urun_marka_id, self.urun_modeli_id, self.seri_no]):
            return
        
        # Ürün parkında arama yap
        urun_parki = self.env['servis.urun'].search([
            ('tur_id', '=', self.urun_turu_id.id),
            ('marka_id', '=', self.urun_marka_id.id),
            ('model_id', '=', self.urun_modeli_id.id),
            ('serial_no', '=', self.seri_no),
        ], limit=1)
        
        if urun_parki:
            # Ürün parkında kayıtlı - güncelle
            update_vals = {}
            if not urun_parki.musteri_id:
                update_vals['musteri_id'] = self.musteri_id.id
            # Garanti başlama tarihi varsa ve henüz atanmamışsa, gelen tarihi ayarla
            if garanti_baslama_tarihi and not urun_parki.garanti_baslama:
                update_vals['garanti_baslama'] = garanti_baslama_tarihi
            
            if update_vals:
                urun_parki.write(update_vals)
            # Zaten kayıtlıysa yapma, sessiz geç
        else:
            # Ürün parkında yok - yeni kayıt oluştur
            try:
                self.env['servis.urun'].create({
                    'tur_id': self.urun_turu_id.id,
                    'marka_id': self.urun_marka_id.id,
                    'model_id': self.urun_modeli_id.id,
                    'serial_no': self.seri_no,
                    'musteri_id': self.musteri_id.id,
                    'garanti_baslama': garanti_baslama_tarihi if garanti_baslama_tarihi else fields.Date.today(),
                })
            except Exception as e:
                # Hata oluşsa bile sessiz geç, otomatik işlem olduğu için user notification gösterme
                _logger.warning(f"Otomatik ürün parkı kaydı başarısız: {str(e)}")

    def action_barkod_etiketi_preview(self):
        """PDF olarak barkod etiketini açar"""
        return {
            'type': 'ir.actions.act_url',
            'url': f'/report/pdf/servis_takip.report_barkod_etiketi/{self.id}?download=false',
            'target': 'new',
        }

