from odoo import models, fields, api

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    # Şimdilik örnek bir alan ekleyelim ki boş görünmesin
    module_servis_yonetimi_ozellikleri = fields.Boolean(
        string="Gelişmiş Servis Özellikleri",
        help="Servis yönetimi için ek özellikleri aktif eder."
    )

    # Ayarın adı: urun_parki_kayit_politikasi
    urun_parki_kayit_politikasi = fields.Selection([
        ('kayit_et', 'Otomatik Kayıt Et'),
        ('kayit_etme', 'Kayıt Etme')
    ], string="Yeni Ürün Parkı Kayıt Politikası", 
       default='kayit_et',
       config_parameter='servis_takip.urun_parki_kayit_politikasi')

