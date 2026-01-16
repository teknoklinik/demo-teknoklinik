# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError

class ServisUrunAktarWizard(models.TransientModel):
    _name = 'servis.urun.aktar.wizard'
    _description = 'Servis Ürün Aktarma Sihirbazı'

    arama_tipi = fields.Selection([
        ('sn', 'Seri No (S/N)'),
        ('musteri', 'Kontak Adı'),
        ('barcode', 'Barkod No'),
        ('urun_tip', 'Ürün Tipi'),
        ('urun_marka', 'Marka')
    ], string="Ara", required=True, default='sn')

    arama_metni = fields.Char("Arama Metni", help="En az 2 karakter giriniz.")

    urun_line_ids = fields.One2many(
        'servis.urun.aktar.wizard.line', 
        'wizard_id', 
        string="Bulunan Ürün Kayıtları"
    )

    @api.onchange('arama_metni', 'arama_tipi')
    def _onchange_arama_metni(self):
        domain = []
        if self.arama_metni:
                if self.arama_tipi == 'sn':
                    domain = [('serial_no', 'ilike', self.arama_metni)]
                elif self.arama_tipi == 'barcode':
                    domain = [('barcode', 'ilike', self.arama_metni)]
                elif self.arama_tipi == 'musteri':
                    domain = [('musteri_adi', 'ilike', self.arama_metni)]
                elif self.arama_tipi == 'urun_marka':
                    # Marka tablosundaki isme göre ara
                    domain = [('marka_id.name', 'ilike', self.arama_metni)]
                elif self.arama_tipi == 'urun_tip':
                    # Ürün türü tablosundaki isme göre ara
                    domain = [('tur_id.name', 'ilike', self.arama_metni)]

        found_products = self.env['servis.urun'].search(domain, limit=80)

        lines = []
        for urun in found_products:
            # BURASI KRİTİK: urun_id'ye urun.id değerini veriyoruz
            lines.append((0, 0, {
                'urun_real_id': urun.id,
                'urun_tipi': urun.tur_id.name or 'Belirsiz',
                'name': urun.name,
                'musteri_adi': urun.musteri_adi,
                'serial_no': urun.serial_no,
                'marka_model': f"{urun.marka_id.name or ''} / {urun.model_id.name or ''}",
                'garanti_durumu': urun.garanti_durumu,
                'secildi': False,
            }))
        
        # Önce mevcutları sil, sonra yenileri ekle
        self.urun_line_ids = [(5, 0, 0)] + lines

    def action_urun_aktar(self):
        selected_lines = self.urun_line_ids.filtered(lambda l: l.secildi)
        
        if not selected_lines:
            raise UserError(_("Lütfen aktarmak için bir ürün seçiniz!"))

        if len(selected_lines) > 1:
            raise UserError(_("Aynı anda sadece 1 ürün aktarabilirsiniz."))

        # SEÇİLEN WIZARD SATIRI
        line = selected_lines[0]
        
        # ASIL ÜRÜN KAYDI (urun_id alanını buradan alıyoruz)
        if not line.urun_real_id:
            raise UserError(_("Ürün ID bulunamadı."))

        urun = self.env['servis.urun'].browse(line.urun_real_id)

        if not urun.exists():
            raise UserError(_("Seçilen ürün sistemde bulunamadı."))
        
        # EĞER urun_id hala boşsa (senin logunda olduğu gibi), durdur ve uyar
        if not urun:
            raise UserError(_("Seçilen satırın asıl ürün kaydı bulunamadı! (urun_id is empty)"))
        
        # HEDEF SERVİS KAYDI (Context üzerinden)
        active_id = self.env.context.get('active_id')
        active_model = self.env.context.get('active_model') or 'servis.kaydi'
        
        if not active_id:
            raise UserError(_("Hedef servis kaydı bulunamadı. Lütfen sihirbazı tekrar açın."))
        
        servis_kaydi = self.env[active_model].browse(active_id)
        
        if servis_kaydi.exists():
            values = {
                'musteri_tipi': urun.musteri_tipi,
                'musteri_id': urun.musteri_id.id if urun.musteri_id else False,
                'urun_turu_id': urun.tur_id.id if urun.tur_id else False,
                'urun_marka_id': urun.marka_id.id if urun.marka_id else False,
                'urun_modeli_id': urun.model_id.id if urun.model_id else False,
                'seri_no': urun.serial_no,
                'barkod_no': urun.barcode,
                'garanti_baslama': urun.garanti_baslama,
                'garanti_suresi': urun.garanti_suresi,
            }

            try:
                # Veriyi yaz ve sayfayı yenile
                servis_kaydi.with_context(skip_required_check=True).sudo().write(values)
            except Exception as e:
                raise UserError(_("Veri aktarılırken hata oluştu: %s") % str(e))
        else:
            raise UserError(_("Güncellenecek servis kaydı sistemde bulunamadı."))

        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

class ServisUrunAktarWizardLine(models.TransientModel):
    _name = 'servis.urun.aktar.wizard.line'
    _description = 'Ürün Aktarma Satırı'

    wizard_id = fields.Many2one('servis.urun.aktar.wizard', ondelete='cascade')
    urun_real_id = fields.Integer(readonly=True)
    urun_tipi = fields.Char("Ürün Tipi")
    name = fields.Char("Ürün Adı")
    musteri_adi = fields.Char("Müşteri")
    serial_no = fields.Char("Seri No")
    marka_model = fields.Char("Marka / Model")
    garanti_durumu = fields.Char("Garanti Durumu")
    secildi = fields.Boolean("Seçildi", default=False)

