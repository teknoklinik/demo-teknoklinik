from odoo import models, fields, api, _
import random

class UrunTuru(models.Model):
    _name = 'urun.turu'
    _description = 'Ürün Türü'
    _order = 'name'

    name = fields.Char(string='Ürün Türü Adı', required=True)


class UrunMarkasi(models.Model):
    _name = 'urun.markasi'
    _description = 'Ürün Markası'
    _order = 'name'

    name = fields.Char(string='Marka Adı', required=True)
    tur_id = fields.Many2one('urun.turu', string='Ürün Türü', required=True, ondelete='cascade')

class UrunModeli(models.Model):
    _name = 'urun.modeli'
    _description = 'Ürün Tanımları'
    _order = 'id desc'

    # ID gösterimi için alan
    display_id = fields.Integer(string='ID', readonly=True, store=True)

    # Temel 3 Sütun
    tur_id = fields.Many2one('urun.turu', string='Ürün Türü', required=True)
    marka_id = fields.Many2one(
        'urun.markasi', 
        string='Marka', 
        required=True,
        domain="[('tur_id', '=', tur_id)]"
    )
    name = fields.Char(string='Model Adı', required=True)

    @api.model_create_multi
    def create(self, vals_list):
        """ Kayıt oluşturulduğunda ID'yi display_id alanına yazar """
        records = super(UrunModeli, self).create(vals_list)
        for record in records:
            record.display_id = record.id
        return records

    def action_download_import_template(self):
        """ Excel şablonu indirme fonksiyonu """
        return {
            'type': 'ir.actions.act_url',
            'url': '/urunler/static/urun_modeli_template.xlsx', 
            'target': 'new', 
        }

    @api.onchange('tur_id')
    def _onchange_tur_id(self):
        """ Tür değiştiğinde markayı sıfırla """
        if self.tur_id:
            self.marka_id = False

    _sql_constraints = [
        ('name_marka_tur_uniq', 
         'unique(name, marka_id, tur_id)', 
         'Hata: Bu Ürün Türü, Marka ve Model kombinasyonu sistemde zaten mevcut!')
    ]



