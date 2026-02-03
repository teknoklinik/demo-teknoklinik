from odoo import models, fields, api


class OzelNotebookSatiri(models.Model):
    _name = 'servis.ozel.notebook.satiri'
    _description = 'Servis Kaydı Özel Notebook Satırı'
    _order = 'create_date asc'  # Girme sırasına göre (eskiden yeni'ye)

    # İlişkiler - Hangi notebook'a ait?
    servis_kaydi_id = fields.Many2one(
        'servis.kaydi',
        string='Servis Kaydı',
        required=True,
        ondelete='cascade'
    )
    
    notebook_type = fields.Selection([
        ('notebook_1', 'Raporlama'),
    ], string='Notebook Tipi', required=False, default='notebook_1')

    # Form alanları
    kolon = fields.Selection([
        ('alan1', 'Özel Alan 1'),
        ('alan2', 'Özel Alan 2'),
        ('alan3', 'Özel Alan 3'),
        ('alan4', 'Özel Alan 4'),
        ('alan5', 'Özel Alan 5'),
        ('alan6', 'Özel Alan 6'),
    ], string='Değer', help='Değer seçiniz')
    
    aciklama = fields.Text(
        string='Açıklama',
        help='Açıklama yazınız'
    )
    
    personel_id = fields.Many2one(
        'res.users',
        string='Kullanıcı',
        default=lambda self: self.env.user,
        readonly=True
    )

    def _get_kolon_listesi(self):
        """Dinamik alan değer listesi - özelleştirmeden isimleri al"""
        ozellestirme = self.env['servis.ozellestirme'].get_ozellestirme()
        return [
            ('alan1', ozellestirme.ozel_alan_1_adi or 'Özel Alan 1'),
            ('alan2', ozellestirme.ozel_alan_2_adi or 'Özel Alan 2'),
            ('alan3', ozellestirme.ozel_alan_3_adi or 'Özel Alan 3'),
            ('alan4', ozellestirme.ozel_alan_4_adi or 'Özel Alan 4'),
            ('alan5', ozellestirme.ozel_alan_5_adi or 'Özel Alan 5'),
            ('alan6', ozellestirme.ozel_alan_6_adi or 'Özel Alan 6'),
        ]

    @api.model
    def fields_get(self, allfields=None, attributes=None):
        """Kolon field'ının selection'ını dinamik hale getir - zaten kullanılan değerleri filtrele"""
        result = super().fields_get(allfields, attributes)
        if 'kolon' in result:
            result['kolon']['selection'] = self._get_kolon_listesi()
        return result
    
    def _get_filtered_kolon_choices(self):
        """Mevcut kayıtta zaten kullanılan değerleri filtrele"""
        if not self.servis_kaydi_id:
            return self._get_kolon_listesi()
        
        # Bu kaydında zaten kullanılan değerleri al
        used_values = self.search([
            ('servis_kaydi_id', '=', self.servis_kaydi_id.id),
            ('notebook_type', '=', self.notebook_type),
            ('id', '!=', self.id)  # Kendisi hariç
        ]).mapped('kolon')
        
        # Tüm seçeneklerden kullanılanları çıkar
        all_choices = self._get_kolon_listesi()
        return [(code, label) for code, label in all_choices if code not in used_values]

    def write(self, vals):
        """Her yazma işleminde parent cache'ini temizle ve duplikat kontrol et"""
        # Kolon değeri değiştiriliyorsa, duplikat kontrol et
        if 'kolon' in vals:
            for record in self:
                # Aynı servis_kaydi_id'de başka satırlarda aynı kolon değeri var mı?
                duplicate = self.search([
                    ('servis_kaydi_id', '=', record.servis_kaydi_id.id),
                    ('kolon', '=', vals['kolon']),
                    ('notebook_type', '=', record.notebook_type),
                    ('id', '!=', record.id)  # Kendisi hariç
                ])
                
                if duplicate:
                    from odoo.exceptions import ValidationError
                    raise ValidationError(
                        f"Bu değer bu kaydında zaten kullanılıyor! "
                        f"Her değer sadece 1 kere kullanılabilir."
                    )
        
        result = super().write(vals)
        
        # Parent servis.kaydi records'ını invalidate et
        parent_records = self.env['servis.kaydi'].search([('ozel_notebook_1_satiri_ids', 'in', self.ids)])
        if parent_records:
            parent_records._compute_ozel_alan_degerleri()
        
        return result

    def create(self, vals_list):
        """Yeni satır oluşturulurken duplikat kontrol et"""
        for vals in vals_list:
            if 'kolon' in vals and 'servis_kaydi_id' in vals:
                # Aynı servis_kaydi_id'de bu kolon değeri var mı?
                duplicate = self.search([
                    ('servis_kaydi_id', '=', vals['servis_kaydi_id']),
                    ('kolon', '=', vals['kolon']),
                    ('notebook_type', '=', vals.get('notebook_type', 'notebook_1'))
                ])
                
                if duplicate:
                    from odoo.exceptions import ValidationError
                    raise ValidationError(
                        f"Bu değer bu kaydında zaten kullanılıyor! "
                        f"Her değer sadece 1 kere kullanılabilir."
                    )
        
        return super().create(vals_list)
