from odoo import models, fields, api

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    # 'module_' ekini sildik, sadece ayar ismi yaptık
    is_advanced_service_features = fields.Boolean(
        string="Gelişmiş Servis Özellikleri",
        config_parameter='servis_takip.is_advanced_service_features'
    )

    urun_parki_kayit_politikasi = fields.Selection([
        ('kayit_et', 'Otomatik Kayıt Et'),
        ('kayit_etme', 'Kayıt Etme')
    ], string="Yeni Ürün Parkı Kayıt Politikası", 
       default='kayit_et',
       config_parameter='servis_takip.urun_parki_kayit_politikasi')

    fatura_urun_parki_kayit_politikasi = fields.Selection([
        ('kayit_et', 'Otomatik Kayıt Et'),
        ('kayit_etme', 'Kayıt Etme')
    ], string="Fatura Oluştururken Ürün Parkı Kayıt Politikası", 
       default='kayit_etme',
       config_parameter='servis_takip.fatura_urun_parki_kayit_politikasi')

    servis_sure_asimi_limiti = fields.Integer(
        string="Servis Süre Aşımı Sınırı (Gün)",
        default=21,
        config_parameter='servis_takip.servis_sure_asimi_limiti',
        help="Bu günden daha fazla süredir serviste olan cihazlar için uyarı gösterilir"
    )