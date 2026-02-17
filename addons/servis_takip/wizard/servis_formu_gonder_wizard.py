from odoo import models, fields, api
from odoo.exceptions import UserError
import base64


class ServisFormuGonderWizard(models.TransientModel):
    _name = 'servis.formu.gonder.wizard'
    _description = 'Servis Formu Gönder Wizard'

    servis_kaydi_id = fields.Many2one('servis.kaydi', string='Servis Kaydı', required=True)
    musteri_id = fields.Many2one('res.partner', string='Müşteri', related='servis_kaydi_id.musteri_id', readonly=True)
    musteri_email = fields.Char(string='E-Posta', required=False)
    musteri_telefon = fields.Char(string='Telefon Numarası', required=False)
    email_degisti = fields.Boolean(string='Email Değişti', compute='_compute_degisti', store=False)
    telefon_degisti = fields.Boolean(string='Telefon Değişti', compute='_compute_degisti', store=False)
    
    gonder_kabul_formu = fields.Boolean(string='Kabul Formu', default=False)
    gonder_teslim_formu = fields.Boolean(string='Teslim Formu', default=False)
    
    gonder_email = fields.Boolean(string='E-Posta ile Gönder', default=True)
    gonder_whatsapp = fields.Boolean(string='WhatsApp ile Gönder', default=False)

    @api.depends('musteri_id', 'musteri_email', 'musteri_telefon')
    def _compute_degisti(self):
        for record in self:
            if record.musteri_id:
                record.email_degisti = record.musteri_email != record.musteri_id.email
                record.telefon_degisti = record.musteri_telefon != record.musteri_id.phone
            else:
                record.email_degisti = False
                record.telefon_degisti = False

    @api.onchange('servis_kaydi_id')
    def _onchange_servis_kaydi(self):
        """Mevcut formlara göre checkboxları otomatik işaretle ve müşteri bilgilerini doldur"""
        if self.servis_kaydi_id:
            # Müşteri bilgilerini doldur
            if self.servis_kaydi_id.musteri_id:
                self.musteri_email = self.servis_kaydi_id.musteri_id.email
                self.musteri_telefon = self.servis_kaydi_id.musteri_id.phone

            # Kabul formu varsa işaretle
            kabul_formu = self.env['kabul.formu'].search([
                ('servis_id', '=', self.servis_kaydi_id.id)
            ], limit=1)
            self.gonder_kabul_formu = bool(kabul_formu)

            # Teslim formu varsa işaretle
            teslim_formu = self.env['teslim.formu'].search([
                ('servis_id', '=', self.servis_kaydi_id.id)
            ], limit=1)
            self.gonder_teslim_formu = bool(teslim_formu)

    def action_guncelle_iletisim(self):
        """Email ve telefon numarasını kontak kaydında güncelle"""
        if not self.musteri_id:
            raise UserError('Müşteri bilgisi bulunamadı!')
        
        vals = {}
        if self.musteri_email != self.musteri_id.email:
            vals['email'] = self.musteri_email
        if self.musteri_telefon != self.musteri_id.phone:
            vals['phone'] = self.musteri_telefon
        
        if vals:
            self.musteri_id.write(vals)
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Başarılı',
                'message': 'Müşteri iletişim bilgileri güncellendi.',
                'type': 'success',
                'sticky': False,
            }
        }

    def action_gonder(self):
        """Secilen formlari musteriye gonder"""
        self.ensure_one()

        if not self.gonder_kabul_formu and not self.gonder_teslim_formu:
            raise UserError('Lutfen en az bir form seciniz!')

        if not self.gonder_email and not self.gonder_whatsapp:
            raise UserError('Lutfen en az bir gonderim yontemi seciniz!')

        if not self.musteri_email and self.gonder_email:
            raise UserError('E-Posta gonderimi secili oldugu halde e-posta adresi bulunamadi!')

        if not self.musteri_telefon and self.gonder_whatsapp:
            raise UserError('WhatsApp gonderimi secili oldugu halde telefon numarasi bulunamadi!')

        formlar_gonderildi = []

        # 1. Formlari arka planda isle (E-posta gonderimi vs.)
        if self.gonder_kabul_formu:
            self._gonder_formu(
                self.servis_kaydi_id,
                'kabul',
                'servis_takip.report_kabul_formu_template'
            )
            formlar_gonderildi.append('Kabul Formu')

        if self.gonder_teslim_formu:
            self._gonder_formu(
                self.servis_kaydi_id,
                'teslim',
                'servis_takip.report_teslim_formu_template'
            )
            formlar_gonderildi.append('Teslim Formu')

        # 2. WhatsApp seciliyse TEK BIR AKSYON olustur (Mesaj burada birlestiriliyoruz)
        if self.gonder_whatsapp:
            # Secilen formlari metin olarak birlestir
            form_metni = " ve ".join(formlar_gonderildi)
            
            # Telefonu temizle
            telefon = ''.join(filter(str.isdigit, self.musteri_telefon))
            if len(telefon) == 10 and telefon.startswith('5'):
                telefon = '90' + telefon
            elif len(telefon) == 11 and telefon.startswith('05'):
                telefon = '9' + telefon

            # Mesaji olustur
            mesaj = (
                f"Merhaba {self.musteri_id.name},\n\n"
                f"*{self.servis_kaydi_id.name}* numarali servis kaydınıza ait *{form_metni}* hazırlanmıştır. "
                f"Form detayları e-posta adresinize gonderilmistir.\n\n"
                f"Bizi tercih ettiğiniz için teşekkür ederiz."
            )
            
            import urllib.parse
            encoded_mesaj = urllib.parse.quote(mesaj)
            # api.whatsapp yerine web.whatsapp kullanımı mesajın kutuya düşmesini garantiler
            whatsapp_url = f"https://web.whatsapp.com/send?phone={telefon}&text={encoded_mesaj}"
            
            return {
                'type': 'ir.actions.act_url',
                'url': whatsapp_url,
                'target': 'new',
            }

        # 3. Sadece E-Posta seçiliyse başarı mesajı göster
        mesaj_sonuc = '\n'.join(formlar_gonderildi) + '\n\n'
        mesaj_sonuc += f"✓ E-Posta: {self.musteri_email}\n"

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Formlar Gönderildi',
                'message': mesaj_sonuc,
                'type': 'success',
                'sticky': False,
            }
        }

    def _gonder_formu(self, servis_kaydi, formu_tipi, report_name):
        """Formu mail veya whatsapp ile gönder"""
        
        try:
            pdf_content, _ = self.env['ir.actions.report']._render_qweb_pdf(report_name, res_ids=servis_kaydi.ids)
        except Exception as e:
            raise UserError(f"PDF oluşturulurken hata oluştu: {str(e)}\n"
                            f"Lütfen '{report_name}' isimli raporun doğru tanımlandığından emin olun.")

        dosya_adi = f"{servis_kaydi.name}-{formu_tipi.capitalize()}-Formu.pdf"

        # E-Posta gönder
        if self.gonder_email:
            self._gonder_email(servis_kaydi, formu_tipi, pdf_content, dosya_adi)

        # WhatsApp gönder
        if self.gonder_whatsapp:
            return self._gonder_whatsapp(servis_kaydi, formu_tipi)
        
        return False

    def _gonder_email(self, servis_kaydi, formu_tipi, pdf_content, dosya_adi):
        """Mail ile formu gönder ve eki ekle"""
        if not self.musteri_email:
            raise UserError(f'Müşterinin e-posta adresi bulunamadı!')

        # 1. PDF verisini Base64 formatına çevir (Hatanın çözümü burası)
        # Odoo attachmentları base64 formatında saklar.
        try:
            pdf_base64 = base64.b64encode(pdf_content)
        except Exception:
            # Eğer zaten base64 gelmişse veya hata oluşursa ham içeriği koru
            pdf_base64 = pdf_content

        # 2. PDF Ekini (Attachment) Oluştur
        attachment = self.env['ir.attachment'].create({
            'name': dosya_adi,
            'datas': pdf_base64, # Base64'e dönüştürülmüş veri
            'res_model': 'servis.kaydi',
            'res_id': servis_kaydi.id,
            'type': 'binary',
            'mimetype': 'application/pdf', # Dosya tipini açıkça belirtelim
        })

        # 3. Mail Nesnesini Oluştur ve Eki Bağla
        mail_vals = {
            'subject': f"{servis_kaydi.name} - {formu_tipi.capitalize()} Formu",
            'body_html': f"""
                <p>Merhaba {self.musteri_id.name},</p>
                <p>Teknik servis kaydı <strong>{servis_kaydi.name}</strong> için hazırlanan formu ekte sunulmuştur.</p>
                <p>Saygılarımızla,<br/>Teknik Servis Takip Sistemi</p>
            """,
            'email_from': self.env.company.email or 'noreply@example.com',
            'email_to': self.musteri_email,
            'attachment_ids': [(6, 0, [attachment.id])],
        }

        mail = self.env['mail.mail'].create(mail_vals)
        mail.send()

    def _gonder_whatsapp(self, servis_kaydi, formu_tipi):
        """WhatsApp Web üzerinden mesaj gönderimini başlatır"""
        if not self.musteri_telefon:
            raise UserError(f'Müşterinin telefon numarası bulunamadı!')

        # 1. Telefon numarasını sadece rakamlardan oluşacak şekilde temizle
        telefon = ''.join(filter(str.isdigit, self.musteri_telefon))
        
        # Türkiye formatı kontrolü: 5xx ile başlıyorsa 90 ekle, 05xx ise 9 ile değiştir
        if len(telefon) == 10 and telefon.startswith('5'):
            telefon = '90' + telefon
        elif len(telefon) == 11 and telefon.startswith('05'):
            telefon = '9' + telefon

        # 2. Mesaj metnini oluştur
        mesaj = (
            f"Merhaba {self.musteri_id.name},\n\n"
            f"*{servis_kaydi.name}* numaralı servis kaydınız için "
            f"*{formu_tipi.lower()}* formu hazırlanmıştır. "
            f"Detaylar e-posta adresinize gönderilmiştir.\n\n"
            f"Bizi tercih ettiğiniz için teşekkür ederiz."
        )
        
        # 3. WhatsApp Linkini Oluştur (wa.me linki daha kararlı çalışır)
        import urllib.parse
        encoded_mesaj = urllib.parse.quote(mesaj)
        
        # 'send?phone=' yerine doğrudan '/numara' yapısı bazen daha hızlı tetikler
        whatsapp_url = f"https://web.whatsapp.com/send?phone={telefon}&text={encoded_mesaj}"

        # 4. Kullanıcıyı bu linke yönlendir
        return {
            'type': 'ir.actions.act_url',
            'url': whatsapp_url,
            'target': 'new',
        }

