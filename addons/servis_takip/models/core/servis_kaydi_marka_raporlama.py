from odoo import models, fields, api
from datetime import datetime

# Marka Raporlama Durumları (Sabit - Kod tarafından belirlenir)
MARKA_RAPORLAMA_DURUM = [
    ('mgs_giris', 'Marka Garanti Sistemi Giriş'),
    ('mgs_cikis', 'Marka Garanti Sistemi Çıkış'),
    ('mgs_hakedis', 'Marka Garanti Sistemi Hakediş'),
    ('kargo_giris', 'Kargo Giriş'),
    ('kargo_cikis', 'Kargo Çıkış'),
    ('kargo_hakedis', 'Kargo Hakediş'),
]


class ServisKaydiMarkaRaporlama(models.Model):
    _name = 'servis.kaydi.marka.raporlama'
    _description = 'Servis Kaydı Marka Raporlama'

    servis_kaydi_id = fields.Many2one('servis.kaydi', required=True, ondelete='cascade')
    durum = fields.Selection(MARKA_RAPORLAMA_DURUM, string='Marka Raporlama', required=True)
    aciklama = fields.Text(string='Açıklama')
    tarih = fields.Datetime(string='Tarih', readonly=True, default=lambda self: datetime.now())
    personel_id = fields.Many2one('hr.employee', string='İlgili Personel', readonly=True, default=lambda self: self.env['hr.employee'].search([('user_id', '=', self.env.user.id)], limit=1))
