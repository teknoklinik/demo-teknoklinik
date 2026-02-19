from odoo import models, fields, api


class ServisKaydiKargolar(models.Model):
    _name = 'servis.kaydi.kargolar'
    _description = 'Servis Kaydı Kargolar'
    _order = 'create_date asc'

    servis_kaydi_id = fields.Many2one(
        'servis.kaydi',
        string='Servis Kaydı',
        required=True,
        ondelete='cascade'
    )

    kargo_turu = fields.Selection([
        ('giris', 'Kargo Giriş'),
        ('cikis', 'Kargo Çıkış'),
    ], string='Kargo Türü', help='Kargo giriş veya çıkışı seçiniz', required=True)
    
    kargo_firmasi_id = fields.Many2one(
        'kargo.firmasi',
        string='Kargo Firması',
        domain=[('aktif', '=', True)]
    )
    
    servis_form_no = fields.Char(
        string='Servis Form No',
        compute='_compute_servis_form_no',
        store=False,
        readonly=True
    )
    
    tarih = fields.Datetime(
        string='Tarih',
        default=lambda self: fields.Datetime.now(),
        readonly=True
    )
    
    tutar = fields.Monetary(string='Tutar', currency_field='company_currency_id')
    
    company_currency_id = fields.Many2one(
        'res.currency',
        string='Para Birimi',
        related='servis_kaydi_id.company_currency_id',
        store=False
    )
    
    kargo_fis = fields.Char(string='Kargo Fiş')
    
    kargo_irsaliye = fields.Char(string='Kargo İrsaliye')
    
    durum = fields.Selection([
        ('onaylandi', 'Onaylandı'),
        ('onaylanmadi', 'Onaylanmadı'),
    ], string='Durumu')
    
    garanti_durumu = fields.Char(
        string='Garanti Durumu',
        compute='_compute_garanti_durumu',
        store=False,
        readonly=True
    )

    def _compute_servis_form_no(self):
        """Servis formunun form numarasını getir"""
        for record in self:
            record.servis_form_no = record.servis_kaydi_id.name if record.servis_kaydi_id else ''
    
    def _compute_garanti_durumu(self):
        """Servis kaydındaki garanti durumunu getir"""
        for record in self:
            if record.servis_kaydi_id:
                if record.servis_kaydi_id.garanti_durumu == 'devam':
                    record.garanti_durumu = 'Garantisi Var'
                else:
                    record.garanti_durumu = 'Garanti Yok'
            else:
                record.garanti_durumu = ''
