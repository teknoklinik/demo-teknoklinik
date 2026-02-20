# -*- coding: utf-8 -*-
from odoo import models, fields, api
from datetime import datetime, timedelta

class ServisDashboard(models.TransientModel):
    _name = 'servis.dashboard'
    _description = 'Servis Yönetimi Dashboard'

    # Tarih aralığı seçimi
    date_from = fields.Date(string='Başlangıç Tarihi', default=lambda self: fields.Date.today() - timedelta(days=30))
    date_to = fields.Date(string='Bitiş Tarihi', default=fields.Date.today)

    # İstatistik Alanları
    # Genel Sayılar
    toplam_servis_kaydi = fields.Integer(string='Toplam Servis Kaydı', compute='_compute_toplam_servis_kaydi', store=False)
    aktif_servis_sayisi = fields.Integer(string='Aktif Servis Sayısı', compute='_compute_aktif_servis_sayisi', store=False)
    teslim_edilen_sayisi = fields.Integer(string='Teslim Edilen', compute='_compute_teslim_edilen_sayisi', store=False)
    iptal_edilen_sayisi = fields.Integer(string='İptal Edilen', compute='_compute_iptal_edilen_sayisi', store=False)

    # Garanti İstatistikleri
    garanti_yok_sayisi = fields.Integer(string='Garantisi Yok', compute='_compute_garanti_yok_sayisi', store=False)
    garanti_devam_sayisi = fields.Integer(string='Garantisi Devam', compute='_compute_garanti_devam_sayisi', store=False)
    
    # Ödeme ve Tutar
    toplam_tutar = fields.Float(string='Toplam Tutar', compute='_compute_toplam_tutar', store=False)
    odenmis_tutar = fields.Float(string='Ödenmiş Tutar', compute='_compute_odenmis_tutar', store=False)
    odenmeyen_tutar = fields.Float(string='Ödenmemiş Tutar', compute='_compute_odenmeyen_tutar', store=False)

    # Zaman İstatistikleri
    ortalama_servis_suresi = fields.Float(string='Ort. Servis Süresi (Gün)', compute='_compute_ortalama_servis_suresi', store=False)
    sure_asimi_sayisi = fields.Integer(string='Süre Aşımı Olan', compute='_compute_sure_asimi_sayisi', store=False)

    # Müşteri İstatistikleri
    toplam_musteri_sayisi = fields.Integer(string='Toplam Müşteri', compute='_compute_toplam_musteri_sayisi', store=False)
    
    # Ürün İstatistikleri
    en_cok_servise_gelen_urun = fields.Char(string='En Çok Servise Gelen Ürün', compute='_compute_en_cok_servise_gelen_urun', store=False)

    # ===== COMPUTED FIELDS =====
    
    @api.depends('date_from', 'date_to')
    def _compute_toplam_servis_kaydi(self):
        """Verilen tarih aralığında toplam servis kaydı sayısı"""
        for record in self:
            count = self.env['servis.kaydi'].search_count([
                ('create_date', '>=', record.date_from),
                ('create_date', '<=', record.date_to)
            ])
            record.toplam_servis_kaydi = count

    @api.depends('date_from', 'date_to')
    def _compute_aktif_servis_sayisi(self):
        """Aktif (teslim edilmemiş) servis sayısı"""
        for record in self:
            count = self.env['servis.kaydi'].search_count([
                ('state', 'not in', ['teslim_edildi', 'iptal']),
                ('create_date', '>=', record.date_from),
                ('create_date', '<=', record.date_to)
            ])
            record.aktif_servis_sayisi = count

    @api.depends('date_from', 'date_to')
    def _compute_teslim_edilen_sayisi(self):
        """Teslim edilen servis sayısı"""
        for record in self:
            count = self.env['servis.kaydi'].search_count([
                ('state', '=', 'teslim_edildi'),
                ('teslim_tarihi', '>=', record.date_from),
                ('teslim_tarihi', '<=', record.date_to)
            ])
            record.teslim_edilen_sayisi = count

    @api.depends('date_from', 'date_to')
    def _compute_iptal_edilen_sayisi(self):
        """İptal edilen servis sayısı"""
        for record in self:
            count = self.env['servis.kaydi'].search_count([
                ('state', '=', 'iptal'),
                ('create_date', '>=', record.date_from),
                ('create_date', '<=', record.date_to)
            ])
            record.iptal_edilen_sayisi = count

    @api.depends('date_from', 'date_to')
    def _compute_garanti_yok_sayisi(self):
        """Garantisi yok olan servis sayısı"""
        for record in self:
            kayitlar = self.env['servis.kaydi'].search([
                ('create_date', '>=', record.date_from),
                ('create_date', '<=', record.date_to)
            ])
            # Python'da filtreleme (SQL'de kullanılamaz)
            count = len(kayitlar.filtered(lambda x: x.garanti_durumu == 'yok'))
            record.garanti_yok_sayisi = count

    @api.depends('date_from', 'date_to')
    def _compute_garanti_devam_sayisi(self):
        """Garantisi devam eden servis sayısı"""
        for record in self:
            kayitlar = self.env['servis.kaydi'].search([
                ('create_date', '>=', record.date_from),
                ('create_date', '<=', record.date_to)
            ])
            # Python'da filtreleme (SQL'de kullanılamaz)
            count = len(kayitlar.filtered(lambda x: x.garanti_durumu == 'devam'))
            record.garanti_devam_sayisi = count

    @api.depends('date_from', 'date_to')
    def _compute_toplam_tutar(self):
        """Toplam servis tutarı"""
        for record in self:
            kayitlar = self.env['servis.kaydi'].search([
                ('create_date', '>=', record.date_from),
                ('create_date', '<=', record.date_to)
            ])
            record.toplam_tutar = sum(kayitlar.mapped('genel_toplam'))

    @api.depends('date_from', 'date_to')
    def _compute_odenmis_tutar(self):
        """Ödenmiş tutar (fatura ile ödenmiş olanlar)"""
        for record in self:
            kayitlar = self.env['servis.kaydi'].search([
                ('create_date', '>=', record.date_from),
                ('create_date', '<=', record.date_to),
                ('state', '=', 'teslim_edildi')
            ])
            # Basit hesaplama: teslim edilen tutarlar ödenmiş sayılıyor
            record.odenmis_tutar = sum(kayitlar.mapped('genel_toplam'))

    @api.depends('toplam_tutar', 'odenmis_tutar')
    def _compute_odenmeyen_tutar(self):
        """Ödenmemiş tutar"""
        for record in self:
            record.odenmeyen_tutar = record.toplam_tutar - record.odenmis_tutar

    @api.depends('date_from', 'date_to')
    def _compute_ortalama_servis_suresi(self):
        """Ortalama servis süresi (gün olarak)"""
        for record in self:
            kayitlar = self.env['servis.kaydi'].search([
                ('state', '=', 'teslim_edildi'),
                ('teslim_tarihi', '>=', record.date_from),
                ('teslim_tarihi', '<=', record.date_to)
            ])
            if kayitlar:
                toplam_sure = sum(kayitlar.mapped('serviste_gecen_sure'))
                record.ortalama_servis_suresi = toplam_sure / len(kayitlar)
            else:
                record.ortalama_servis_suresi = 0.0

    @api.depends('date_from', 'date_to')
    def _compute_sure_asimi_sayisi(self):
        """Süre aşımı olan aktif servis sayısı"""
        for record in self:
            kayitlar = self.env['servis.kaydi'].search([
                ('state', 'not in', ['teslim_edildi', 'iptal'])
            ])
            # Python'da filtreleme (sure_asimi_var computed field)
            count = len(kayitlar.filtered(lambda x: x.sure_asimi_var == True))
            record.sure_asimi_sayisi = count

    @api.depends('date_from', 'date_to')
    def _compute_toplam_musteri_sayisi(self):
        """Farklı müşteri sayısı"""
        for record in self:
            kayitlar = self.env['servis.kaydi'].search([
                ('create_date', '>=', record.date_from),
                ('create_date', '<=', record.date_to)
            ])
            musteri_ids = set(kayitlar.mapped('musteri_id.id'))
            record.toplam_musteri_sayisi = len(musteri_ids)

    @api.depends('date_from', 'date_to')
    def _compute_en_cok_servise_gelen_urun(self):
        """En çok servise gelen ürün"""
        for record in self:
            kayitlar = self.env['servis.kaydi'].search([
                ('create_date', '>=', record.date_from),
                ('create_date', '<=', record.date_to)
            ])
            urun_sayilari = {}
            for kayit in kayitlar:
                if kayit.urun_modeli_id:
                    urun_adi = kayit.urun_modeli_id.name
                    urun_sayilari[urun_adi] = urun_sayilari.get(urun_adi, 0) + 1
            
            if urun_sayilari:
                en_cok = max(urun_sayilari, key=urun_sayilari.get)
                record.en_cok_servise_gelen_urun = f"{en_cok} ({urun_sayilari[en_cok]})"
            else:
                record.en_cok_servise_gelen_urun = "-"
