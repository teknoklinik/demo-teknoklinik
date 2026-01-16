from odoo import models, fields, api, _
from datetime import timedelta

class ServisIslemTipi(models.Model):
    _name = 'servis.islem.tipi'
    _description = 'Servis İşlem Tipi Tanımları'
    _rec_name = 'name'
    name = fields.Char(string='İşlem Tipi Adı', required=True)
    aktif = fields.Boolean(string='Aktif', default=True)

class ServisIslemSatiri(models.Model):
    _name = 'servis.islem.satiri'
    _description = 'Servis İşlem Kayıt Satırı'
    _order = 'tarih asc, id asc'  

    servis_kaydi_id = fields.Many2one(
        'servis.kaydi', 
        string='Servis Kaydı', 
        required=True, 
        ondelete='cascade'
    )
    islem_tipi_id = fields.Many2one('servis.islem.tipi', string='İşlem Tipi')
    tarih = fields.Datetime(
        string='Başlangıç Tarihi', 
        default=fields.Datetime.now,
        readonly=True 
    )
    bitis_tarihi = fields.Datetime(string='Bitiş Tarihi')
    gecen_sure = fields.Char(
        string='Toplam Süre', 
        compute='_compute_gecen_sure', 
        store=True,
        readonly=True
    )
    aciklama = fields.Text(string='Açıklama / Not')
    
    personel_id = fields.Many2one(
        'res.users', 
        string='İlgili Personel', 
        default=lambda self: self.env.user,
        required=True,
        readonly=True 
    )

    tablo_duzenle = fields.Boolean(related='servis_kaydi_id.tablo_duzenle', store=False)

    @api.depends('tarih', 'bitis_tarihi')
    def _compute_gecen_sure(self):
        for record in self:
            record.gecen_sure = False
            if record.tarih and record.bitis_tarihi:
                start_dt = fields.Datetime.from_string(record.tarih)
                end_dt = fields.Datetime.from_string(record.bitis_tarihi)
                if end_dt < start_dt:
                    record.gecen_sure = "Hata: Bitiş < Başlangıç"
                    continue
                delta = end_dt - start_dt
                days = delta.days
                seconds = delta.seconds
                hours = seconds // 3600
                minutes = (seconds % 3600) // 60
                parts = []
                if days: parts.append(f"{days} Gün")
                if hours: parts.append(f"{hours} Saat")
                if minutes: parts.append(f"{minutes} Dakika")
                record.gecen_sure = " ".join(parts) if parts else "0 Dakika"
            else:
                record.gecen_sure = False
                
    @api.model_create_multi
    def create(self, vals_list):
        current_user = self.env.user
        for vals in vals_list:
            if not vals.get('personel_id'):
                vals['personel_id'] = current_user.id
            if not vals.get('tarih'):
                vals['tarih'] = fields.Datetime.now()
        
        records = super().create(vals_list)
        for record in records:
            servis_id = record.servis_kaydi_id.id
            yeni_baslangic_tarihi = record.tarih
            onceki_satirlar = self.search([
                ('servis_kaydi_id', '=', servis_id),
                ('id', '!=', record.id),
                ('tarih', '<', yeni_baslangic_tarihi),
                ('bitis_tarihi', '=', False) 
            ], order='tarih desc', limit=1)
            
            if onceki_satirlar:
                onceki_satirlar.write({'bitis_tarihi': yeni_baslangic_tarihi - timedelta(seconds=1)})
        return records
    
    # POPUP BUTON FONKSİYONLARI
    def action_tabloyu_ac_popup(self):
        """Popup içinden kilit açar ve ekranı yeniler"""
        self.ensure_one()
        self.servis_kaydi_id.write({'tablo_duzenle': True})
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'servis.islem.satiri',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
            'context': self.env.context,
        }

    def action_tabloyu_kilitle_popup(self):
        """Popup içinden kilidi kapatır ve ana ekranı yeniler"""
        self.ensure_one()
        self.servis_kaydi_id.write({'tablo_duzenle': False})
        return {'type': 'ir.actions.client', 'tag': 'reload'}

    def action_save_and_refresh(self):
        """Yeni kayıt oluşturulduğunda çalışır"""
        self.ensure_one()
        if self.servis_kaydi_id:
            self.servis_kaydi_id.write({'tablo_duzenle': False})
        return {'type': 'ir.actions.client', 'tag': 'reload'}
    
    def action_close_wizard(self):
        return {'type': 'ir.actions.act_window_close'}
        

