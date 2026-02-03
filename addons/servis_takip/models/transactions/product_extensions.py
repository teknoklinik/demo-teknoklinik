from odoo import models, fields, api
from datetime import date
import logging

_logger = logging.getLogger(__name__)


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    # --- Dövizli Satış Fiyatı Alanları ---
    custom_currency_id = fields.Many2one(
        'res.currency', 
        string="Döviz Para Birimi",
        default=lambda self: self.env['res.currency'].search([('name', '=', 'USD')], limit=1),
        help="Ürün fiyatını bu para biriminde girmeniz için seçiniz (USD, EUR, GBP, vb.)"
    )
    
    # --- Vergiler Dahil Fiyat Alanı ---
    price_with_tax = fields.Float(
        string='Vergiler Dahil Fiyat',
        digits='Product Price',
        help='Vergiler dahil toplam fiyat (TL) - otomatik hesaplanır veya elle girilebilir'
    )

    price_with_tax_display = fields.Char(
        compute='_compute_price_with_tax_display',
        string='Vergiler Dahil Fiyat'
    )

    @api.onchange('list_price', 'taxes_id')
    def _onchange_calculate_price_with_tax(self):
        """Satış fiyatı değiştiğinde vergiler dahil fiyatı otomatik hesapla"""
        if self.list_price:
            # Vergi toplamını hesapla
            tax_amount = 0.0
            for tax in self.taxes_id:
                tax_amount += tax.compute_all(self.list_price, product=self)['total_included'] - self.list_price
            self.price_with_tax = self.list_price + tax_amount

    @api.onchange('price_with_tax', 'taxes_id')
    def _onchange_calculate_list_price(self):
        """Vergiler dahil fiyat değiştiğinde satış fiyatını geri hesapla"""
        if self.price_with_tax and self.taxes_id:
            # Vergi toplamını hesapla
            tax_amount = 0.0
            for tax in self.taxes_id:
                tax_amount += tax.compute_all(self.price_with_tax / (1 + sum(t.amount for t in self.taxes_id) / 100), product=self)['total_included'] - self.price_with_tax / (1 + sum(t.amount for t in self.taxes_id) / 100)
            # Vergisiz fiyat = vergiler dahil fiyat / (1 + vergi oranı)
            total_tax_rate = sum(t.amount for t in self.taxes_id) / 100
            if total_tax_rate > 0:
                self.list_price = self.price_with_tax / (1 + total_tax_rate)
            else:
                self.list_price = self.price_with_tax
        elif self.price_with_tax and not self.taxes_id:
            self.list_price = self.price_with_tax

    custom_list_price = fields.Float(
        string="Satış Fiyatı Döviz", 
        digits='Product Price',
        help="Seçilen döviz cinsinden fiyat giriniz. Otomatik olarak TL'ye çevrilecektir."
    )

    @api.onchange('custom_list_price', 'custom_currency_id')
    def _onchange_custom_price(self):
        """Dövizli fiyat girildiğinde TL karşılığını (list_price) otomatik hesaplar"""
        if self.custom_list_price and self.custom_currency_id:
            try:
                company_currency = self.env.company.currency_id
                # Odoo'nun built-in currency conversion metodunu kullan
                converted_price = self.custom_currency_id._convert(
                    self.custom_list_price,
                    company_currency,
                    self.env.company,
                    date.today()
                )
                self.list_price = converted_price
                _logger.info(
                    f"Döviz Dönüşümü (Satış): {self.custom_list_price} {self.custom_currency_id.name} "
                    f"= {converted_price} {company_currency.name}"
                )
            except Exception as e:
                _logger.warning(f"Döviz dönüşümü başarısız oldu: {str(e)}")
                pass

    @api.onchange('list_price', 'custom_currency_id')
    def _onchange_list_price_to_custom(self):
        """Satış fiyatından döviz karşılığını otomatik hesapla"""
        if self.list_price and self.custom_currency_id:
            try:
                company_currency = self.env.company.currency_id
                converted_price = company_currency._convert(
                    self.list_price,
                    self.custom_currency_id,
                    self.env.company,
                    date.today()
                )
                self.custom_list_price = converted_price
            except Exception as e:
                _logger.warning(f"Ters döviz dönüşümü başarısız oldu: {str(e)}")
                pass

    # --- Dövizli Maliyet Alanları ---
    custom_cost_currency_id = fields.Many2one(
        'res.currency', 
        string="Maliyet Döviz Para Birimi",
        default=lambda self: self.env['res.currency'].search([('name', '=', 'USD')], limit=1),
        help="Ürün maliyetini bu para biriminde girmeniz için seçiniz (USD, EUR, GBP, vb.)"
    )
    
    custom_cost_price = fields.Float(
        string="Maliyet Döviz", 
        digits='Product Price',
        help="Seçilen döviz cinsinden maliyet giriniz. Otomatik olarak TL'ye çevrilecektir."
    )

    # --- Maliyet Vergileri Alanları ---
    cost_taxes_id = fields.Many2many(
        'account.tax',
        'product_cost_tax_rel',
        'product_id',
        'tax_id',
        string="Maliyet Vergileri",
        domain=[('type_tax_use', '=', 'purchase')],
        help="Ürün maliyeti üzerine uygulanacak vergiler"
    )

    cost_with_tax = fields.Float(
        string='Vergiler Dahil Maliyet',
        digits='Product Price',
        help='Vergiler dahil toplam maliyet (TL) - otomatik hesaplanır veya elle girilebilir'
    )

    cost_with_tax_display = fields.Char(
        compute='_compute_cost_with_tax_display',
        string='Vergiler Dahil Maliyet'
    )

    @api.onchange('standard_price', 'cost_taxes_id')
    def _onchange_calculate_cost_with_tax(self):
        """Maliyet fiyatı değiştiğinde vergiler dahil maliyeti otomatik hesapla"""
        if self.standard_price:
            # Vergi toplamını hesapla
            tax_amount = 0.0
            for tax in self.cost_taxes_id:
                tax_amount += tax.compute_all(self.standard_price, product=self)['total_included'] - self.standard_price
            self.cost_with_tax = self.standard_price + tax_amount

    @api.onchange('cost_with_tax', 'cost_taxes_id')
    def _onchange_calculate_standard_price(self):
        """Vergiler dahil maliyet değiştiğinde maliyet fiyatını geri hesapla"""
        if self.cost_with_tax and self.cost_taxes_id:
            # Vergi toplamını hesapla
            total_tax_rate = sum(t.amount for t in self.cost_taxes_id) / 100
            if total_tax_rate > 0:
                self.standard_price = self.cost_with_tax / (1 + total_tax_rate)
            else:
                self.standard_price = self.cost_with_tax
        elif self.cost_with_tax and not self.cost_taxes_id:
            self.standard_price = self.cost_with_tax

    @api.onchange('custom_cost_price', 'custom_cost_currency_id')
    def _onchange_custom_cost_price(self):
        """Dövizli maliyet girildiğinde TL karşılığını (standard_price) otomatik hesaplar"""
        if self.custom_cost_price and self.custom_cost_currency_id:
            try:
                company_currency = self.env.company.currency_id
                # Odoo'nun built-in currency conversion metodunu kullan
                converted_cost = self.custom_cost_currency_id._convert(
                    self.custom_cost_price,
                    company_currency,
                    self.env.company,
                    date.today()
                )
                self.standard_price = converted_cost
                _logger.info(
                    f"Döviz Dönüşümü (Maliyet): {self.custom_cost_price} {self.custom_cost_currency_id.name} "
                    f"= {converted_cost} {company_currency.name}"
                )
            except Exception as e:
                _logger.warning(f"Maliyet döviz dönüşümü başarısız oldu: {str(e)}")
                pass

    @api.onchange('standard_price', 'custom_cost_currency_id')
    def _onchange_cost_price_to_custom(self):
        """Maliyet fiyatından döviz karşılığını otomatik hesapla"""
        if self.standard_price and self.custom_cost_currency_id:
            try:
                company_currency = self.env.company.currency_id
                converted_cost = company_currency._convert(
                    self.standard_price,
                    self.custom_cost_currency_id,
                    self.env.company,
                    date.today()
                )
                self.custom_cost_price = converted_cost
            except Exception as e:
                _logger.warning(f"Ters maliyet döviz dönüşümü başarısız oldu: {str(e)}")
                pass

    # --- Display Fields for List View ---
    custom_list_price_display = fields.Char(
        compute='_compute_list_price_display',
        string='Satış Fiyatı Döviz'
    )
    
    custom_cost_price_display = fields.Char(
        compute='_compute_cost_price_display',
        string='Maliyet Döviz'
    )

    @api.depends('custom_list_price', 'custom_currency_id')
    def _compute_list_price_display(self):
        for record in self:
            if record.custom_list_price and record.custom_currency_id:
                record.custom_list_price_display = f"{record.custom_list_price:.2f} {record.custom_currency_id.symbol}"
            else:
                record.custom_list_price_display = ""

    @api.depends('custom_cost_price', 'custom_cost_currency_id')
    def _compute_cost_price_display(self):
        for record in self:
            if record.custom_cost_price and record.custom_cost_currency_id:
                record.custom_cost_price_display = f"{record.custom_cost_price:.2f} {record.custom_cost_currency_id.symbol}"
            else:
                record.custom_cost_price_display = ""

    @api.depends('price_with_tax')
    def _compute_price_with_tax_display(self):
        for record in self:
            if record.price_with_tax:
                company_currency = record.company_id.currency_id or self.env.company.currency_id
                record.price_with_tax_display = f"{record.price_with_tax:.2f} {company_currency.symbol}"
            else:
                record.price_with_tax_display = ""

    @api.depends('cost_with_tax')
    def _compute_cost_with_tax_display(self):
        for record in self:
            if record.cost_with_tax:
                company_currency = record.company_id.currency_id or self.env.company.currency_id
                record.cost_with_tax_display = f"{record.cost_with_tax:.2f} {company_currency.symbol}"
            else:
                record.cost_with_tax_display = ""






