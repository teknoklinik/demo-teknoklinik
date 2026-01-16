from odoo import models, fields

class UrunNotu(models.Model):    
    _name = 'urun.notu'
    _description = 'Ürün Notları'

    urun_id = fields.Many2one('servis.urun', string='Ürün', required=True, ondelete='cascade')
    konu = fields.Char(string='Konu')
    aciklama = fields.Text(string='Açıklama')
    not_personel_id = fields.Many2one('res.users', string='İlgili Personel', 
                                      default=lambda self: self.env.user, readonly=True)
    not_kayit_tarihi = fields.Datetime(string='Tarih', 
                                       default=fields.Datetime.now, readonly=True)

    def action_save_and_reload(self):
        """Kaydeder ve sayfayı yeniler"""
        self.ensure_one()
        return {'type': 'ir.actions.client', 'tag': 'reload'}

class UrunDokuman(models.Model):
    _name = 'urun.dokuman'
    _description = 'Ürün Dokümanları'
    _order = 'create_date desc'

    urun_id = fields.Many2one('servis.urun', string='Ürün', required=True, ondelete='cascade')
    konu = fields.Char(string='Konu', required=True)
    dokuman_dosya = fields.Binary(string='Dosya', filename='dokuman_dosya_isim', required=True) 
    dokuman_dosya_isim = fields.Char(string='Dosya Adı')
    
    dokuman_personel_id = fields.Many2one('res.users', string='Yükleyen Personel', 
                                           default=lambda self: self.env.user, readonly=True)
    dokuman_tarihi = fields.Datetime(string='Yükleme Tarihi', 
                                     default=fields.Datetime.now, readonly=True)

    def action_save_and_reload(self):
        """Kaydeder ve sayfayı yeniler."""
        self.ensure_one()
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }
    
    def action_preview_document(self):
        """Dokümanı tarayıcıda önizlemek için URL döner"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content/?model=urun.dokuman&id=%s&field=dokuman_dosya&filename_field=dokuman_dosya_isim&download=false' % (self.id),
            'target': 'new', # Yeni sekmede açar
        }

