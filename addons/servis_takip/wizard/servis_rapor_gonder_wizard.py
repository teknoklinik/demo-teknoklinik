from odoo import models, fields, api
from odoo.exceptions import UserError
import base64


class ServisRaporGonderWizard(models.TransientModel):
    _name = 'servis.rapor.gonder.wizard'
    _description = 'Servis Raporu Gönder Wizard'

    servis_kaydi_id = fields.Many2one('servis.kaydi', string='Servis Kaydı', required=True)
    musteri_id = fields.Many2one('res.partner', string='Müşteri', related='servis_kaydi_id.musteri_id', readonly=True)
    musteri_email = fields.Char(string='E-Posta', required=False)
    musteri_telefon = fields.Char(string='Telefon Numarası', required=False)
    email_degisti = fields.Boolean(string='Email Değişti', compute='_compute_degisti', store=False)
    telefon_degisti = fields.Boolean(string='Telefon Değişti', compute='_compute_degisti', store=False)
    
    gonder_kabul_raporu = fields.Boolean(string='Kabul Raporu', default=False)
    gonder_teslim_raporu = fields.Boolean(string='Teslim Raporu', default=False)
    
    gonder_email = fields.Boolean(string='E-Posta ile Gönder', default=True)
    gonder_whatsapp = fields.Boolean(string='WhatsApp ile Gönder', default=False)

    @api.depends('musteri_id', 'musteri_email', 'musteri_telefon')
    def _compute_degisti(self):
        for record in self:
            if record.musteri_id:
                record.email_degisti = record.musteri_email != record.musteri_id.email
                record.telefon_degisti = record.musteri_telefon != record.musteri_id.mobile
            else:
                record.email_degisti = False
                record.telefon_degisti = False

    @api.onchange('servis_kaydi_id')
    def _onchange_servis_kaydi(self):
        """Mevcut raporlara göre checkboxları otomatik işaretle ve müşteri bilgilerini doldur"""
        if self.servis_kaydi_id:
            # Müşteri bilgilerini doldur
            if self.servis_kaydi_id.musteri_id:
                self.musteri_email = self.servis_kaydi_id.musteri_id.email
                self.musteri_telefon = self.servis_kaydi_id.musteri_id.mobile

            # Kabul raporu varsa işaretle
            kabul_rapor = self.env['kabul.rapor'].search([
                ('servis_id', '=', self.servis_kaydi_id.id)
            ], limit=1)
            self.gonder_kabul_raporu = bool(kabul_rapor)

            # Teslim raporu varsa işaretle
            teslim_rapor = self.env['teslim.rapor'].search([
                ('servis_id', '=', self.servis_kaydi_id.id)
            ], limit=1)
            self.gonder_teslim_raporu = bool(teslim_rapor)

    def action_guncelle_iletisim(self):
        """Email ve telefon numarasını kontak kaydında güncelle"""
        if not self.musteri_id:
            raise UserError('Müşteri bilgisi bulunamadı!')
        
        vals = {}
        if self.musteri_email != self.musteri_id.email:
            vals['email'] = self.musteri_email
        if self.musteri_telefon != self.musteri_id.mobile:
            vals['mobile'] = self.musteri_telefon
        
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
        """Seçilen raporları müşteriye gönder"""
        self.ensure_one()

        if not self.gonder_kabul_raporu and not self.gonder_teslim_raporu:
            raise UserError('Lütfen en az bir rapor seçiniz!')

        if not self.gonder_email and not self.gonder_whatsapp:
            raise UserError('Lütfen en az bir gönderim yöntemi seçiniz!')

        if not self.musteri_email and self.gonder_email:
            raise UserError('E-Posta gönderimi seçili olduğu halde e-posta adresi bulunamadı!')

        if not self.musteri_telefon and self.gonder_whatsapp:
            raise UserError('WhatsApp gönderimi seçili olduğu halde telefon numarası bulunamadı!')

        raporlar_gonderildi = []

        # 1. Raporları arka planda işle (E-posta gönderimi vs.)
        if self.gonder_kabul_raporu:
            self._gonder_rapor(
                self.servis_kaydi_id,
                'kabul',
                'servis_takip.report_kabul_raporu_template'
            )
            raporlar_gonderildi.append('Kabul Raporu')

        if self.gonder_teslim_raporu:
            self._gonder_rapor(
                self.servis_kaydi_id,
                'teslim',
                'servis_takip.report_teslim_raporu_template'
            )
            raporlar_gonderildi.append('Teslim Raporu')

        # 2. WhatsApp seçiliyse TEK BİR AKSİYON oluştur (Mesajı burada birleştiriyoruz)
        if self.gonder_whatsapp:
            # Seçilen raporları metin olarak birleştir
            rapor_metni = " ve ".join(raporlar_gonderildi)
            
            # Telefonu temizle
            telefon = ''.join(filter(str.isdigit, self.musteri_telefon))
            if len(telefon) == 10 and telefon.startswith('5'):
                telefon = '90' + telefon
            elif len(telefon) == 11 and telefon.startswith('05'):
                telefon = '9' + telefon

            # Mesajı oluştur
            mesaj = (
                f"Merhaba {self.musteri_id.name},\n\n"
                f"*{self.servis_kaydi_id.name}* numaralı servis kaydınıza ait *{rapor_metni}* hazırlanmıştır. "
                f"Rapor detayları e-posta adresinize gönderilmiştir.\n\n"
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
        mesaj_sonuc = '\n'.join(raporlar_gonderildi) + '\n\n'
        mesaj_sonuc += f"✓ E-Posta: {self.musteri_email}\n"

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Raporlar Gönderildi',
                'message': mesaj_sonuc,
                'type': 'success',
                'sticky': False,
            }
        }

    def _gonder_rapor(self, servis_kaydi, rapor_tipi, report_name):
        """Raporu mail veya whatsapp ile gönder"""
        
        try:
            pdf_content, _ = self.env['ir.actions.report']._render_qweb_pdf(report_name, res_ids=servis_kaydi.ids)
        except Exception as e:
            raise UserError(f"PDF oluşturulurken hata oluştu: {str(e)}\n"
                            f"Lütfen '{report_name}' isimli raporun doğru tanımlandığından emin olun.")

        dosya_adi = f"{servis_kaydi.name}-{rapor_tipi.capitalize()}-Raporu.pdf"

        # E-Posta gönder
        if self.gonder_email:
            self._gonder_email(servis_kaydi, rapor_tipi, pdf_content, dosya_adi)

        # WhatsApp gönder
        if self.gonder_whatsapp:
            return self._gonder_whatsapp(servis_kaydi, rapor_tipi)
        
        return False

    def _gonder_email(self, servis_kaydi, rapor_tipi, pdf_content, dosya_adi):
        """Mail ile rapor gönder ve eki ekle"""
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
            'subject': f"{servis_kaydi.name} - {rapor_tipi.capitalize()} Raporu",
            'body_html': f"""
                <p>Merhaba {self.musteri_id.name},</p>
                <p>Teknik servis kaydı <strong>{servis_kaydi.name}</strong> için hazırlanan rapor ekte sunulmuştur.</p>
                <p>Saygılarımızla,<br/>Teknik Servis Takip Sistemi</p>
            """,
            'email_from': self.env.company.email or 'noreply@example.com',
            'email_to': self.musteri_email,
            'attachment_ids': [(6, 0, [attachment.id])],
        }

        mail = self.env['mail.mail'].create(mail_vals)
        mail.send()

    def _gonder_whatsapp(self, servis_kaydi, rapor_tipi):
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
            f"*{rapor_tipi.lower()}* raporu hazırlanmıştır. "
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

