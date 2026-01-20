from odoo import models, fields


class ServisKaydiAksesuar(models.Model):
    _name = 'servis.kaydi.aksesuar'
    _description = 'Servis Kaydı Aksesuarları'

    servis_kaydi_id = fields.Many2one('servis.kaydi', string='Servis Kaydı', required=True, ondelete='cascade')
    aksesuar_id = fields.Many2one('servis.aksesuar', string='Aksesuar', required=True)
    miktar = fields.Integer(string='Miktar', default=1)
    sequence = fields.Integer(string='Sıra', default=10)

    class Meta:
        ordering = ['sequence', 'id']
