from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

class ServisOdemeWizard(models.TransientModel):
    _name = 'servis.odeme.wizard'
    _description = 'Servis Kaydı Ödeme Onayı ve Teslimat Sihirbazı'

    servis_kaydi_id = fields.Many2one(
        'servis.kaydi', 
        string='Servis Kaydı', 
        required=True, 
        readonly=True
    )

    # Para Birimi Alanı
    company_currency_id = fields.Many2one(
        'res.currency', 
        string='Para Birimi', 
        related='servis_kaydi_id.company_currency_id', 
        readonly=True
    )
    
    # DÜZELTME 1: Hesaplamadaki Alan Adı Hatası Giderildi
    odenecek_tutar = fields.Monetary(
        string='Ödenecek Tutar', 
        currency_field='company_currency_id', 
        # required=True kaldırıldı, çünkü compute alanları genelde context'ten değer alır veya hesaplanır.
        readonly=True,
        compute='_compute_odenecek_tutar',
        store=True # Context'ten gelen default değeri alması için store=True tutulabilir.
    )
    
    # GARANTİ KONTROL ALANI
    garanti_kapsaminda = fields.Boolean(
        string="Garanti Kapsamında mı?",
        compute='_compute_garanti_kapsaminda',
        store=False, 
        help="Servis kaydı garanti kapsamında ise ödeme onayı gerekmeyecektir."
    )
    
    # DÜZELTME 2: 'required=True' Kaldırıldı. Zorunluluk artık sadece XML'de koşullu olarak yönetilecek.
    odeme_alindi = fields.Boolean(
        string='Ödeme Alındı Onayı', 
        default=False,
        help="Müşteriden hizmet bedelinin tahsil edildiğini onaylayın."
    )
    
    teslimat_notu = fields.Text(
        string='Teslimat Notu', 
        help="Teslimat sırasındaki özel durumlar veya notlar."
    )
    # Compute Metotları
    @api.depends('servis_kaydi_id')
    def _compute_garanti_kapsaminda(self):
        """Servis Kaydındaki garanti durumunu sihirbaza aktarır."""
        for record in self:
            record.garanti_kapsaminda = record.servis_kaydi_id.garanti_kapsami if record.servis_kaydi_id else False

    @api.depends('servis_kaydi_id')
    def _compute_odenecek_tutar(self):
        """
        Servis Kaydındaki gerçekleşen maliyeti (gerceklesen_maliyet) okur.
        Garanti kapsamında ise tutarı sıfır olarak yansıtır.
        """
        for record in self:
            tutar = 0.0
            if record.servis_kaydi_id:
                # KRİTİK DÜZELTME: 'teknik_ucret' yerine 'gerceklesen_maliyet' kullanıldı.
                maliyet = record.servis_kaydi_id.gerceklesen_maliyet
                
                if not record.servis_kaydi_id.garanti_kapsami:
                    tutar = maliyet
            
            record.odenecek_tutar = tutar
    # İşlem Metotları
    def action_odeme_onayla_ve_teslim_et(self):
        """
        Ödeme onayını gerçekleştirir ve ilgili servis kaydını kapatır.
        """
        self.ensure_one()
        
        # Garanti kontrolü: Eğer garanti kapsamında değilse VE ödeme alınmadıysa uyarı ver.
        if not self.garanti_kapsaminda and not self.odeme_alindi:
            raise UserError(_("Kayıt garanti kapsamında değildir. Lütfen müşteriden ödemenin alındığını onaylayın."))
            
        kayit = self.servis_kaydi_id
        
        # Güncellenecek verileri hazırla
        vals = {
            # Ödeme alındı/teslimat yapıldı durumunu Servis Kaydı'na kaydet.
            'odeme_yapildi': True, 
        }
        
        # Teslimat notunu ekle
        if self.teslimat_notu:
            # Mevcut açıklamaya yeni notu ekle
            mevcut_aciklama = kayit.servis_aciklamasi or ""
            # Mevcut açıklamayı sadece ekleme yapıyorsanız değiştirmeye gerek yok, log tutmak daha iyidir.
            # Ancak, siz 'servis_aciklamasi' alanını kullanmak istediğiniz için yapıyı koruyorum:
            vals['servis_aciklamasi'] = f"{mevcut_aciklama}\n\n[Teslimat Notu - {fields.Date.today()}]: {self.teslimat_notu}"

        # 1. Servis kaydını güncelle
        kayit.write(vals)
        
        # 2. Kaydı kapatma metodunu çağır (Durumu 'teslim_edildi' yapar)
        kayit.action_kaydi_kapat() 
        
        return {'type': 'ir.actions.act_window_close'}

