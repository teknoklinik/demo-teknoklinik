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
