from odoo import models, fields, api, _
from datetime import timedelta
import re
import random

# 1. Kod tarafında korunan sabit durumlar
SERVIS_DURUM_SELECTION = [
    ('kayit_yapildi', 'Servis Kayıt Yapıldı'),
    ('inceleme', 'İncelemede'),
    ('onay_bekliyor', 'Onay Bekleniyor'),
    ('islemde', 'İşlemde'),
    ('islem_tamamlandi', 'İşlem Tamamlandı'),
    ('odeme_bekliyor', 'Ödeme Bekliyor'),
    ('teslim_edildi', 'Teslim Edildi'),
    ('iptal', 'İptal Edildi'),
]

DURUM_RENK_MAP = {
    'kayit_yapildi': 3,       # Sarı (Yeni/Dikkat çeken başlangıç)
    'inceleme': 4,            # Açık Mavi (Analiz süreci)
    'onay_bekliyor': 2,       # Turuncu (Karar/Bekleme noktası)
    'islemde': 8,             # Koyu Mavi (Aktif çalışma/Efor)
    'islem_tamamlandi': 5,    # Mor (Teknik iş bitti, sonraki adıma hazır)
    'odeme_bekliyor': 2,      # Turuncu (Finansal bekleme)
    'teslim_edildi': 10,      # Yeşil (Başarıyla kapandı)
    'iptal': 1,               # Kırmızı (Negatif kapanış)
}

class ServisDurumTanimi(models.Model):
    """Kullanıcının arayüzden ekleyeceği yeni durumlar burada tutulur"""
    _name = 'servis.durum.tanimi'
    _description = 'Ekstra Servis Durumları'
    _order = 'sequence'

    name = fields.Char(string='Durum Adı', required=True)
    key = fields.Char(string='Durum Kodu')
    sequence = fields.Integer(string='Sıra', default=100)
    active = fields.Boolean(default=True, string="Aktif")
    color = fields.Integer(
        string='Renk İndeksi', 
        default=lambda self: self._get_default_color()
    )
    def _get_default_color(self):
        """0 ile 11 arasında rastgele bir renk indeksi döner"""
        return random.randint(1, 11)

    @api.onchange('name')
    def _onchange_name(self):
        """İsim girildiğinde Türkçe karakterleri düzeltip otomatik kod üretir"""
        if self.name:
            # Türkçe karakter dönüşümü ve temizleme
            s = self.name.lower()
            tr_map = str.maketrans("çğışıöü ", "cgisiou_")
            s = s.translate(tr_map)
            s = re.sub(r'[^a-z0-9_]', '', s) # Sadece harf, rakam ve alt çizgi
            self.key = s

class ServisDurumSatiri(models.Model):
    _name = 'servis.durum.satiri'
    _description = 'Servis Kaydı Durum Geçmişi Satırı'
    _order = 'tarih asc, id asc' 

    servis_kaydi_id = fields.Many2one(
        'servis.kaydi', 
        string='Servis Kaydı',
        required=True,
        ondelete='cascade'
    )

    # Many2one üzerinden seçim yaparak hem sabitleri hem eklenenleri yönetiriz
    state_id = fields.Many2one(
        'servis.durum.tanimi', 
        string='Durum (Dinamik)',
        help="Arayüzden eklenen durumlar için kullanılır."
    )

    # Mevcut yapını korumak için Selection alanını tutuyoruz
    # Ancak seçim listesini bir fonksiyonla besliyoruz (Dinamik hale getiriyoruz)
    state = fields.Selection(
        selection='_get_durum_listesi',
        string='Durum',
        required=True,
    )

    def _get_durum_listesi(self):
        """Mevcut Selection listesi ile veritabanındaki yeni durumları birleştirir"""
        # Önce koddaki sabit listeyi alalım
        selection = list(SERVIS_DURUM_SELECTION)
        # Veritabanına kullanıcı tarafından eklenenleri çekelim
        ekstra_durumlar = self.env['servis.durum.tanimi'].search([])
        for durum in ekstra_durumlar:
            # Eğer kodda olmayan bir key/isim ise listeye ekle
            selection.append((str(durum.id), durum.name))
        return selection

    ariza_tanimi_id = fields.Many2one(
        'servis.ariza.tanimi', 
        string='Arıza Tipi'
    )
    
    personel_id = fields.Many2one(
        'hr.employee', 
        string='İlgili Personel',
        default=lambda self: self.env.user.employee_ids[:1].id if self.env.user.employee_ids else False,
        required=True,
        readonly=True
    )

    tarih = fields.Datetime(
        string='Başlangıç Tarihi',
        default=lambda self: fields.Datetime.now(),
        required=True,
        readonly=True 
    )
    
    bitis_tarihi = fields.Datetime(
        string='Bitiş Tarihi', 
        readonly=True,
        copy=False
    )
    
    gecen_sure = fields.Char(
        string='Toplam Süre',
        compute='_compute_gecen_sure',
        store=True,
        copy=False
    )
    
    aciklama = fields.Text(string='Açıklama / Not')
    tablo_duzenle = fields.Boolean(related='servis_kaydi_id.tablo_duzenle', store=False)
    
    @api.depends('tarih', 'bitis_tarihi')
    def _compute_gecen_sure(self):
        for record in self:
            record.gecen_sure = False
            if record.tarih and record.bitis_tarihi:
                delta = record.bitis_tarihi - record.tarih
                days = delta.days
                hours, remainder = divmod(delta.seconds, 3600)
                minutes, _ = divmod(remainder, 60)
                record.gecen_sure = f"{days} Gün {hours} Saat {minutes} Dakika"

    @api.model_create_multi
    def create(self, vals_list):
        current_employee = self.env.user.employee_id # employee_ids[:1] yerine daha güvenli
        
        for vals in vals_list:
            # 1. Eksik Personel ve Tarih bilgilerini tamamla
            if not vals.get('personel_id') and current_employee: 
                vals['personel_id'] = current_employee.id
            if not vals.get('tarih'):
                vals['tarih'] = fields.Datetime.now()
                
            # 2. ÖNEMLİ: Eğer durum (state) boş geliyorsa varsayılanı zorla ata
            if not vals.get('state'):
                vals['state'] = 'kayit_yapildi'
            
            # 3. ÖNEMLİ: Eğer açıklama boş geliyorsa (çıkıp girince boş kalmaması için)
            if not vals.get('aciklama'):
                vals['aciklama'] = 'Servis kaydı oluşturuldu.'

        # Veritabanına yazma işlemi
        records = super(ServisDurumSatiri, self).create(vals_list)
        
        # Yazma sonrası işlemler
        for record in records:
            # Ana kaydın durumunu satırdaki durumla eşitle
            if record.servis_kaydi_id and record.state:
                # write metodu veritabanına kalıcı yazar
                record.servis_kaydi_id.write({'state': record.state})

            # Tarihleri zincirleme güncelleme mantığı (senin mevcut kodun)
            onceki_satirlar = self.search([
                ('servis_kaydi_id', '=', record.servis_kaydi_id.id),
                ('id', '!=', record.id),
                ('tarih', '<', record.tarih),
                ('bitis_tarihi', '=', False) 
            ], order='tarih desc', limit=1)
            
            if onceki_satirlar:
                onceki_satirlar.write({'bitis_tarihi': record.tarih - timedelta(seconds=1)})
                
        return records

    def write(self, vals):
        res = super(ServisDurumSatiri, self).write(vals)
        if 'state' in vals:
            for record in self:
                if record.servis_kaydi_id:
                    record.servis_kaydi_id.write({'state': record.state})
        return res

    def action_tabloyu_ac_popup(self):
        self.ensure_one()
        self.servis_kaydi_id.write({'tablo_duzenle': True})
        return {
            'name': _('Durum Satırı Düzenle'),
            'type': 'ir.actions.act_window',
            'res_model': 'servis.durum.satiri',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
            'context': self.env.context,
        }

    def action_tabloyu_kilitle_popup(self):
        self.ensure_one()
        self.servis_kaydi_id.write({
            'tablo_duzenle': False,
            'state': self.state
        })
        return {'type': 'ir.actions.client', 'tag': 'reload'}

    def action_save_and_refresh(self):
        return {'type': 'ir.actions.client', 'tag': 'reload'}
    
    def name_get(self):
        result = []
        for record in self:
            # Düzenleme modunda görünecek başlık
            name = "Durum Satırı Bilgi"
            result.append((record.id, name))
        return result

