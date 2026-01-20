from odoo import models, fields


class ServisAksesuar(models.Model):
    _name = 'servis.aksesuar'
    _description = 'Servis Aksesuarları'
    _order = 'name asc'

    name = fields.Char(string='Aksesuar Adı', required=True, tracking=True)
    active = fields.Boolean(string='Aktif', default=True)

    _sql_constraints = [
        ('name_unique', 'unique(name)', 'Aksesuar adı benzersiz olmalıdır!'),
    ]

