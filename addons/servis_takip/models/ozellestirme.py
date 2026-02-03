from odoo import models, fields, api


class ServisOzellestirme(models.Model):
    _name = 'servis.ozellestirme'
    _description = 'Servis Özelleştirme'
    _singleton = True  # Sadece 1 record olacak

    ozel_notebook_1_adi = fields.Char(
        string='Özel Notebook 1 Adı',
        default=''
    )
    ozel_notebook_1_gozuksun = fields.Boolean(
        string='Özel Notebook 1 Görünür',
        default=False
    )

    # 6 Özel Alan Adı (Dropdown için)
    ozel_alan_1_adi = fields.Char(string='Özel Alan 1 Adı', default='Özel Alan 1')
    ozel_alan_2_adi = fields.Char(string='Özel Alan 2 Adı', default='Özel Alan 2')
    ozel_alan_3_adi = fields.Char(string='Özel Alan 3 Adı', default='Özel Alan 3')
    ozel_alan_4_adi = fields.Char(string='Özel Alan 4 Adı', default='Özel Alan 4')
    ozel_alan_5_adi = fields.Char(string='Özel Alan 5 Adı', default='Özel Alan 5')
    ozel_alan_6_adi = fields.Char(string='Özel Alan 6 Adı', default='Özel Alan 6')

    # 6 Özel Alan Listede Görünen Adlandırması
    ozel_alan_1_liste_adi = fields.Char(string='Özel Alan 1 Listede Adı', default='Özel Alan 1')
    ozel_alan_2_liste_adi = fields.Char(string='Özel Alan 2 Listede Adı', default='Özel Alan 2')
    ozel_alan_3_liste_adi = fields.Char(string='Özel Alan 3 Listede Adı', default='Özel Alan 3')
    ozel_alan_4_liste_adi = fields.Char(string='Özel Alan 4 Listede Adı', default='Özel Alan 4')
    ozel_alan_5_liste_adi = fields.Char(string='Özel Alan 5 Listede Adı', default='Özel Alan 5')
    ozel_alan_6_liste_adi = fields.Char(string='Özel Alan 6 Listede Adı', default='Özel Alan 6')

    @api.model
    def get_ozellestirme(self):
        """Özelleştirme datasını getir, yoksa yarat"""
        res = self.search([], limit=1)
        if not res:
            res = self.create({})
        return res

    def write(self, vals):
        """Değişiklik yapıldığında servis.kaydi records'larını invalidate et"""
        result = super().write(vals)
        
        if vals:
            # Tüm servis.kaydi records'larının computed field'larını recalculate et
            servis_kaydi_records = self.env['servis.kaydi'].search([])
            
            # Computed field'ları manual trigger et
            servis_kaydi_records._compute_ozel_notebook_labels()
            servis_kaydi_records._compute_ozel_notebook_visibility()
            servis_kaydi_records._compute_ozel_alan_degerleri()
        
        return result

    def kaydet_ve_yenile(self):
        """Kaydet butonu - değişiklikleri kaydet ve sayfayı yenile"""
        # Tüm servis.kaydi records'larını trigger et
        servis_kaydi_records = self.env['servis.kaydi'].search([])
        servis_kaydi_records._compute_ozel_alan_degerleri()
        
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    def get_formview_action(self):
        """Form view'unda top bar'daki başlığı değiştir"""
        action = super().get_formview_action()
        action['name'] = 'Raporlama Özelleştirmesi'
        return action

    @api.model_create_multi
    def create(self, vals_list):
        """Singleton modele birden fazla record yaratılmasını önle"""
        # Eğer zaten record varsa, onu güncelle
        existing = self.search([], limit=1)
        if existing:
            # Birden fazla değer varsa, yalnızca ilk olanı al
            if len(vals_list) > 1:
                vals_list = [vals_list[0]]
            existing.write(vals_list[0] if vals_list else {})
            return existing
        return super().create(vals_list)
