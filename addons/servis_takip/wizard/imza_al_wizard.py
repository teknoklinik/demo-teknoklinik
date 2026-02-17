from odoo import models, fields, api
from odoo.exceptions import UserError


class ImzaAlWizard(models.TransientModel):
    _name = 'imza.al.wizard'
    _description = 'Müşteri İmzası Alma Wizard'

    servis_kaydi_id = fields.Many2one('servis.kaydi', string='Servis Kaydı', required=True)
    musteri_id = fields.Many2one('res.partner', string='Müşteri', related='servis_kaydi_id.musteri_id', readonly=True)
    formu_tipi = fields.Selection([
        ('kabul', 'Kabul Formu'),
        ('teslim', 'Teslim Formu')
    ], string='Form Tipi', required=True)
    
    musteri_imzasi = fields.Binary(string='Müşteri İmzası', help='Müşterinin imzasını buraya çizin')

    @api.onchange('formu_tipi')
    def _onchange_formu_tipi(self):
        """Form tipine göre mevcut imzayı göster"""
        if self.servis_kaydi_id:
            if self.formu_tipi == 'kabul':
                self.musteri_imzasi = self.servis_kaydi_id.kabul_musteri_imzasi
            elif self.formu_tipi == 'teslim':
                self.musteri_imzasi = self.servis_kaydi_id.teslim_musteri_imzasi

    def action_imza_kaydet(self):
        """İmzayı servis kaydına kaydet ve wizard'ı kapat"""
        self.ensure_one()
        
        if not self.musteri_imzasi:
            raise UserError('Lütfen imza alanını doldurunuz!')
        
        # İmzayı servis_kaydi'ye form tipine göre kaydet
        if self.formu_tipi == 'kabul':
            self.servis_kaydi_id.write({
                'kabul_musteri_imzasi': self.musteri_imzasi,
            })
        elif self.formu_tipi == 'teslim':
            self.servis_kaydi_id.write({
                'teslim_musteri_imzasi': self.musteri_imzasi,
            })
        
        # Wizard'ı kapat - başka yere gitme
        return {'type': 'ir.actions.act_window_close'}


