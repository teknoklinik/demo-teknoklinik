from odoo import models, fields, api
from datetime import date
import logging

_logger = logging.getLogger(__name__)


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    def _get_default_tax_20_percent(self):
        """20% satın alma vergisini bul ve döndür"""
        purchase_tax = self.env['account.tax'].search([
            ('type_tax_use', '=', 'purchase'),
            ('amount', '=', 20.0),
            ('active', '=', True)
        ], limit=1)
        return purchase_tax.ids if purchase_tax else []

    def _get_default_sales_tax_20_percent(self):
        """20% satış vergisini bul ve döndür"""
        sales_tax = self.env['account.tax'].search([
            ('type_tax_use', '=', 'sale'),
            ('amount', '=', 20.0),
            ('active', '=', True)
        ], limit=1)
        return sales_tax.ids if sales_tax else []

    @api.model
    def default_get(self, fields_list):
        """Yeni ürün oluşturulurken default değerleri ayarla"""
        defaults = super().default_get(fields_list)
        
        # Satış vergileri için default
        if 'taxes_id' in fields_list:
            defaults['taxes_id'] = [(6, 0, self._get_default_sales_tax_20_percent())]
        
        # Maliyet vergileri için default (supplier_taxes_id)
        if 'supplier_taxes_id' in fields_list:
            defaults['supplier_taxes_id'] = [(6, 0, self._get_default_tax_20_percent())]
        
        return defaults

    def _calculate_tax_fields(self):
        """Vergiler dahil fiyatları otomatik hesapla"""
        for record in self:
            # Satış vergileri dahil fiyatı hesapla
            if record.list_price and record.taxes_id:
                tax_amount = 0.0
                for tax in record.taxes_id:
                    tax_amount += tax.compute_all(record.list_price, product=record)['total_included'] - record.list_price
                record.price_with_tax = record.list_price + tax_amount
            elif record.list_price and not record.taxes_id:
                record.price_with_tax = record.list_price

    @api.model
    def create(self, vals):
        """Ürün oluştururken vergiler dahil fiyatları otomatik hesapla"""
        record = super().create(vals)
        record._calculate_tax_fields()
        return record

    def write(self, vals):
        """Ürün güncellenirken vergiler dahil fiyatları otomatik hesapla"""
        # İçe aktarma sırasında boş alanları default %20 ile doldur
        if 'taxes_id' in vals:
            tax_val = vals.get('taxes_id')
            # Boş kontrol: None, [], [(6, 0, [])]
            is_empty = not tax_val or (isinstance(tax_val, list) and len(tax_val) == 0)
            if is_empty:
                default_taxes = self._get_default_sales_tax_20_percent()
                if default_taxes:
                    vals['taxes_id'] = [(6, 0, default_taxes)]
                    _logger.info(f"taxes_id default %20 atandı")
        
        if 'supplier_taxes_id' in vals:
            supplier_tax_val = vals.get('supplier_taxes_id')
            # Boş kontrol: None, [], [(6, 0, [])]
            is_empty = not supplier_tax_val or (isinstance(supplier_tax_val, list) and len(supplier_tax_val) == 0)
            if is_empty:
                default_taxes = self._get_default_tax_20_percent()
                if default_taxes:
                    vals['supplier_taxes_id'] = [(6, 0, default_taxes)]
                    _logger.info(f"supplier_taxes_id default %20 atandı: {default_taxes}")
        
        result = super().write(vals)
        # Eğer list_price, taxes_id, standard_price güncellenirse hesapla
        if any(key in vals for key in ['list_price', 'taxes_id', 'standard_price']):
            self._calculate_tax_fields()
        return result

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

    website_list_price = fields.Float(
        string='Web Sitesi Satış Fiyatı',
        help='Web sitesinde gösterilecek virgülden sonraki kısmı 00 olarak yuvarlanmış fiyat',
        store=True,
        compute='_compute_website_list_price'
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

    # --- Maliyet Vergileri Alanları (supplier_taxes_id - Native Odoo) ---

    cost_with_tax = fields.Float(
        string='Vergiler Dahil Maliyet',
        digits='Product Price',
        compute='_compute_cost_with_tax',
        inverse='_inverse_cost_with_tax',
        store=True,
        help='Vergiler dahil toplam maliyet (TL) - otomatik hesaplanır veya elle girilebilir'        
    )

    cost_with_tax_display = fields.Char(
        compute='_compute_cost_with_tax_display',
        string='Vergiler Dahil Maliyet'
    )

    @api.depends('standard_price', 'supplier_taxes_id')
    def _compute_cost_with_tax(self):
        """Maliyet fiyatı + satınalma vergileri = vergiler dahil maliyet"""
        for record in self:
            if record.standard_price and record.supplier_taxes_id:
                # Vergi toplamını hesapla
                tax_amount = 0.0
                for tax in record.supplier_taxes_id:
                    tax_amount += tax.compute_all(record.standard_price, product=record)['total_included'] - record.standard_price
                record.cost_with_tax = record.standard_price + tax_amount
            elif record.standard_price and not record.supplier_taxes_id:
                record.cost_with_tax = record.standard_price
            else:
                record.cost_with_tax = 0.0

    def _inverse_cost_with_tax(self):
        """Vergiler dahil maliyet değiştiğinde, vergisiz maliyet'i geri hesapla"""
        for record in self:
            if record.cost_with_tax and record.supplier_taxes_id:
                # Vergi oranını hesapla
                total_tax_rate = sum(t.amount for t in record.supplier_taxes_id) / 100
                if total_tax_rate > 0:
                    record.standard_price = record.cost_with_tax / (1 + total_tax_rate)
                else:
                    record.standard_price = record.cost_with_tax
            elif record.cost_with_tax and not record.supplier_taxes_id:
                record.standard_price = record.cost_with_tax

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

    @api.depends('custom_list_price', 'custom_currency_id')
    def _compute_list_price_display(self):
        for record in self:
            if record.custom_list_price and record.custom_currency_id:
                record.custom_list_price_display = f"{record.custom_list_price:.2f} {record.custom_currency_id.symbol}"
            else:
                record.custom_list_price_display = ""

    custom_cost_price_display = fields.Char(
        compute='_compute_cost_price_display',
        string='Maliyet Döviz'
    )

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

    @api.depends('list_price')
    def _compute_website_list_price(self):
        """Web sitesinde gösterilecek fiyatı virgülden sonraki kısmı 00 olarak yuvarla"""
        for record in self:
            if record.list_price:
                # Fiyatın tam sayı kısmını al
                rounded_price = int(record.list_price)
                record.website_list_price = float(rounded_price)
            else:
                record.website_list_price = 0.0

    # --- Dönüşüm Action Metodları ---
    def action_convert_döviz_to_tl(self):
        """Döviz fiyatlarını TL'ye dönüştür (kur üzerinden çarp)"""
        for record in self:
            company_currency = record.company_id.currency_id or self.env.company.currency_id
            
            # Satış vergileri boşsa default %20 ata
            if not record.taxes_id:
                default_taxes = self._get_default_sales_tax_20_percent()
                if default_taxes:
                    record.taxes_id = [(6, 0, default_taxes)]
            
            # Maliyet vergileri boşsa default %20 ata
            if not record.supplier_taxes_id:
                default_taxes = self._get_default_tax_20_percent()
                if default_taxes:
                    record.supplier_taxes_id = [(6, 0, default_taxes)]
            
            # Satış fiyatı dönüşümü
            if record.custom_list_price and record.custom_currency_id:
                try:
                    converted_price = record.custom_currency_id._convert(
                        record.custom_list_price,
                        company_currency,
                        record.company_id or self.env.company,
                        date.today()
                    )
                    record.list_price = converted_price
                    _logger.info(f"Satış Dönüşümü: {record.custom_list_price} {record.custom_currency_id.name} -> {converted_price} {company_currency.name}")
                except Exception as e:
                    _logger.warning(f"Satış dönüşümü başarısız: {str(e)}")
            
            # Maliyet dönüşümü
            if record.custom_cost_price and record.custom_currency_id:
                try:
                    converted_cost = record.custom_currency_id._convert(
                        record.custom_cost_price,
                        company_currency,
                        record.company_id or self.env.company,
                        date.today()
                    )
                    record.standard_price = converted_cost
                    _logger.info(f"Maliyet Dönüşümü: {record.custom_cost_price} {record.custom_currency_id.name} -> {converted_cost} {company_currency.name}")
                except Exception as e:
                    _logger.warning(f"Maliyet dönüşümü başarısız: {str(e)}")
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Başarılı',
                'message': f'Seçilenleri Dövizden TL\'ye Dönüştürme Tamamlandı ({len(self)} ürün)',
                'type': 'success',
                'sticky': False,
            }
        }

    def action_convert_tl_to_döviz(self):
        """TL fiyatlarını dövize dönüştür (kuru böl)"""
        for record in self:
            company_currency = record.company_id.currency_id or self.env.company.currency_id
            
            # Satış vergileri boşsa default %20 ata
            if not record.taxes_id:
                default_taxes = self._get_default_sales_tax_20_percent()
                if default_taxes:
                    record.taxes_id = [(6, 0, default_taxes)]
            
            # Satış fiyatı dönüşümü
            if record.list_price and record.custom_currency_id:
                try:
                    converted_price = company_currency._convert(
                        record.list_price,
                        record.custom_currency_id,
                        record.company_id or self.env.company,
                        date.today()
                    )
                    record.custom_list_price = converted_price
                    _logger.info(f"Satış Ters Dönüşüm: {record.list_price} {company_currency.name} -> {converted_price} {record.custom_currency_id.name}")
                except Exception as e:
                    _logger.warning(f"Satış ters dönüşümü başarısız: {str(e)}")
            
            # Maliyet vergileri boşsa default %20 ata
            if not record.supplier_taxes_id:
                default_taxes = self._get_default_tax_20_percent()
                if default_taxes:
                    record.supplier_taxes_id = [(6, 0, default_taxes)]
            
            # Maliyet dönüşümü
            if record.standard_price and record.custom_cost_currency_id:
                try:
                    converted_cost = company_currency._convert(
                        record.standard_price,
                        record.custom_cost_currency_id,
                        record.company_id or self.env.company,
                        date.today()
                    )
                    record.custom_cost_price = converted_cost
                    _logger.info(f"Maliyet Ters Dönüşüm: {record.standard_price} {company_currency.name} -> {converted_cost} {record.custom_cost_currency_id.name}")
                except Exception as e:
                    _logger.warning(f"Maliyet ters dönüşümü başarısız: {str(e)}")
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Başarılı',
                'message': f'Seçilenleri TL\'den Dövize Dönüştürme Tamamlandı ({len(self)} ürün)',
                'type': 'success',
                'sticky': False,
            }
        }






