from odoo import models, fields


class KargoFirmasi(models.Model):
    _name = 'kargo.firmasi'
    _description = 'Kargo Firması'
    _order = 'name asc'

    name = fields.Char(string='Firma Adı', required=True, index=True)
    aktif = fields.Boolean(string='Aktif', default=True, index=True)
