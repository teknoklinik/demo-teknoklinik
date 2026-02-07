from odoo import models, fields, api, _
import random

class UrunTuru(models.Model):
    _name = 'urun.turu'
    _description = 'Ürün Türü'
    _order = 'name'

    name = fields.Char(string='Ürün Türü Adı', required=True)
    
    # Reverse relationships for visibility
    marka_ids = fields.One2many('urun.markasi', 'tur_id', string='Markalar', readonly=True)
    modeli_ids = fields.One2many('urun.modeli', 'tur_id', string='Modeller', readonly=True)
    
    def unlink(self):
        """Silmeden önce ilişkili kayıtları warn et"""
        for record in self:
            if record.marka_ids:
                raise ValueError(
                    _('Bu ürün türüne ait %d marka vardır. '
                      'Önce markaları silin veya başka türe taşıyın.') % len(record.marka_ids)
                )
        return super(UrunTuru, self).unlink()


class UrunMarkasi(models.Model):
    _name = 'urun.markasi'
    _description = 'Ürün Markası'
    _order = 'tur_id, name'

    name = fields.Char(string='Marka Adı', required=True)
    tur_id = fields.Many2one('urun.turu', string='Ürün Türü', required=True, ondelete='cascade')
    
    # Reverse relationships for visibility
    modeli_ids = fields.One2many('urun.modeli', 'marka_id', string='Modeller', readonly=True)
    
    def unlink(self):
        """Silmeden önce ilişkili kayıtları warn et"""
        for record in self:
            if record.modeli_ids:
                raise ValueError(
                    _('Bu markaya ait %d model vardır. '
                      'Önce modelleri silin veya başka markaya taşıyın.') % len(record.modeli_ids)
                )
        return super(UrunMarkasi, self).unlink()

class UrunModeli(models.Model):
    _name = 'urun.modeli'
    _description = 'Ürün Modeli'
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
        records = super(UrunModeli, self).create(vals_list)
        for record in records:
            # display_id'yi id oluştuktan sonra güvenli bir şekilde yazalım
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



