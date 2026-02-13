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
        
        if 'taxes_id' in fields_list:
            defaults['taxes_id'] = [(6, 0, self._get_default_sales_tax_20_percent())]
        
        if 'supplier_taxes_id' in fields_list:
            defaults['supplier_taxes_id'] = [(6, 0, self._get_default_tax_20_percent())]
        
        return defaults

    # ==================== SATIŞ FİYATLARI ALANLAR ====================
    
    price_with_tax = fields.Float(
        string='Vergiler Dahil Satış Fiyatı (TL)',
        digits=(12, 0),  # No decimal places
        help='Vergiler dahil toplam satış fiyatı'
    )

    price_with_tax_display = fields.Char(
        compute='_compute_price_with_tax_display',
        string='Vergiler Dahil Satış Fiyatı'
    )

    website_list_price = fields.Float(
        string='Web Sitesi Satış Fiyatı',
        store=True,
        compute='_compute_website_list_price'
    )

    custom_currency_id = fields.Many2one(
        'res.currency', 
        string="Para Birimi",
        default=lambda self: self.env['res.currency'].search([('name', '=', 'USD')], limit=1),
        help="Dövizli fiyatlar için para birimi"
    )
    
    custom_list_price = fields.Float(
        string="Satış Fiyatı Döviz", 
        digits='Product Price',
        help="Seçilen döviz cinsinden satış fiyatı"
    )

    custom_list_price_with_tax = fields.Float(
        string="Vergiler Dahil Satış Fiyatı Döviz",
        digits=(12, 0),  # No decimal places
        help="Seçilen döviz cinsinden vergiler dahil satış fiyatı"
    )

    custom_list_price_display = fields.Char(
        compute='_compute_list_price_display',
        string='Satış Fiyatı Döviz'
    )

    # ==================== MALİYET FİYATLARI ALANLAR ====================

    cost_with_tax = fields.Float(
        string='Vergiler Dahil Maliyet (TL)',
        digits=(12, 0),  # No decimal places
        compute='_compute_cost_with_tax',
        inverse='_inverse_cost_with_tax',
        store=True,
        help='Vergiler dahil toplam maliyet'       
    )

    cost_with_tax_display = fields.Char(
        compute='_compute_cost_with_tax_display',
        string='Vergiler Dahil Maliyet'
    )

    custom_cost_currency_id = fields.Many2one(
        'res.currency', 
        string="Maliyet Para Birimi",
        default=lambda self: self.env['res.currency'].search([('name', '=', 'USD')], limit=1),
        help="Dövizli maliyetler için para birimi"
    )
    
    custom_cost_price = fields.Float(
        string="Maliyet Döviz", 
        digits='Product Price',
        help="Seçilen döviz cinsinden maliyet"
    )

    custom_cost_price_with_tax = fields.Float(
        string="Vergiler Dahil Maliyet Döviz",
        digits=(12, 0),  # No decimal places
        help="Seçilen döviz cinsinden vergiler dahil maliyet"
    )

    custom_cost_price_display = fields.Char(
        compute='_compute_cost_price_display',
        string='Maliyet Döviz'
    )

    # ==================== HELPER METODLAR ====================

    def _get_company_currency(self):
        """Şirket para birimini döndür"""
        return self.company_id.currency_id or self.env.company.currency_id

    def _convert_currency(self, amount, from_currency, to_currency):
        """Para birimi dönüşümü yap - hata durumunda 0 döndür"""
        if not amount or not from_currency or not to_currency:
            return 0.0
        try:
            result = from_currency._convert(
                amount,
                to_currency,
                self.company_id or self.env.company,
                date.today()
            )
            # Round to whole number
            return round(result, 0)
        except Exception as e:
            _logger.warning(f"Para birimi dönüşümü başarısız: {str(e)}")
            return 0.0

    def _calculate_tax_on_amount(self, amount, taxes):
        """Vergiyi hesapla ve vergiler dahil tutarı döndür"""
        if not amount or not taxes:
            return amount
        try:
            tax_amount = 0.0
            for tax in taxes:
                tax_amount += tax.compute_all(amount, product=self)['total_included'] - amount
            # Round to whole number (no decimals)
            return round(amount + tax_amount, 0)
        except Exception:
            return amount

    def _remove_tax_from_amount(self, amount_with_tax, taxes):
        """Vergiler dahil tutardan vergiyi çıkar ve vergisiz tutarı döndür"""
        if not amount_with_tax or not taxes:
            return amount_with_tax
        try:
            total_tax_rate = sum(t.amount for t in taxes) / 100
            if total_tax_rate > 0:
                return amount_with_tax / (1 + total_tax_rate)
            return amount_with_tax
        except Exception:
            return amount_with_tax

    # ==================== COMPUTE METODLAR ====================

    @api.depends('standard_price', 'supplier_taxes_id')
    def _compute_cost_with_tax(self):
        """Maliyet + satınalma vergileri = vergiler dahil maliyet"""
        for record in self:
            record.cost_with_tax = record._calculate_tax_on_amount(
                record.standard_price, 
                record.supplier_taxes_id
            )

    def _inverse_cost_with_tax(self):
        """Vergiler dahil maliyet değiştiğinde, maliyet'i geri hesapla"""
        for record in self:
            record.standard_price = record._remove_tax_from_amount(
                record.cost_with_tax,
                record.supplier_taxes_id
            )

    @api.depends('list_price', 'taxes_id')
    def _compute_price_with_tax_display(self):
        for record in self:
            company_currency = record._get_company_currency()
            if record.price_with_tax:
                record.price_with_tax_display = f"{record.price_with_tax:.0f} {company_currency.symbol}"
            else:
                record.price_with_tax_display = ""

    @api.depends('cost_with_tax')
    def _compute_cost_with_tax_display(self):
        for record in self:
            company_currency = record._get_company_currency()
            if record.cost_with_tax:
                record.cost_with_tax_display = f"{record.cost_with_tax:.0f} {company_currency.symbol}"
            else:
                record.cost_with_tax_display = ""

    @api.depends('list_price')
    def _compute_website_list_price(self):
        """Web sitesinde gösterilecek fiyatı virgülden sonraki kısmı 00 olarak yuvarla"""
        for record in self:
            if record.list_price:
                rounded_price = int(record.list_price)
                record.website_list_price = float(rounded_price)
            else:
                record.website_list_price = 0.0

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

    # ==================== ONCHANGE METODLAR - SATIŞ FİYATLARI ====================

    @api.onchange('list_price', 'taxes_id')
    def _onchange_list_price(self):
        """Satış fiyatı değişince: vergiler dahil satış fiyatını ve dövizleri güncelle"""
        if self.list_price and self.custom_currency_id:
            self.custom_list_price = self._convert_currency(
                self.list_price,
                self._get_company_currency(),
                self.custom_currency_id
            )
        
        self.price_with_tax = self._calculate_tax_on_amount(
            self.list_price,
            self.taxes_id
        )
        
        if self.price_with_tax and self.custom_currency_id:
            self.custom_list_price_with_tax = self._convert_currency(
                self.price_with_tax,
                self._get_company_currency(),
                self.custom_currency_id
            )

    @api.onchange('price_with_tax', 'taxes_id')
    def _onchange_price_with_tax(self):
        """Vergiler dahil satış fiyatı değişince: satış fiyatını ve dövizleri güncelle"""
        self.list_price = self._remove_tax_from_amount(
            self.price_with_tax,
            self.taxes_id
        )
        
        if self.list_price and self.custom_currency_id:
            self.custom_list_price = self._convert_currency(
                self.list_price,
                self._get_company_currency(),
                self.custom_currency_id
            )
        
        if self.price_with_tax and self.custom_currency_id:
            self.custom_list_price_with_tax = self._convert_currency(
                self.price_with_tax,
                self._get_company_currency(),
                self.custom_currency_id
            )

    @api.onchange('custom_list_price', 'custom_currency_id')
    def _onchange_custom_list_price(self):
        """Dövizli satış fiyatı değişince: TL'yi ve diğer tüm fiyatları güncelle"""
        if not self.custom_list_price or not self.custom_currency_id:
            return
        
        company_currency = self._get_company_currency()
        
        self.list_price = self._convert_currency(
            self.custom_list_price,
            self.custom_currency_id,
            company_currency
        )
        
        self.price_with_tax = self._calculate_tax_on_amount(
            self.list_price,
            self.taxes_id
        )
        
        self.custom_list_price_with_tax = self._convert_currency(
            self.price_with_tax,
            company_currency,
            self.custom_currency_id
        )

    @api.onchange('custom_list_price_with_tax', 'custom_currency_id', 'taxes_id')
    def _onchange_custom_list_price_with_tax(self):
        """Dövizli vergiler dahil satış fiyatı değişince: hepsini güncelle"""
        if not self.custom_list_price_with_tax or not self.custom_currency_id:
            return
        
        company_currency = self._get_company_currency()
        
        self.price_with_tax = self._convert_currency(
            self.custom_list_price_with_tax,
            self.custom_currency_id,
            company_currency
        )
        
        self.list_price = self._remove_tax_from_amount(
            self.price_with_tax,
            self.taxes_id
        )
        
        self.custom_list_price = self._convert_currency(
            self.list_price,
            company_currency,
            self.custom_currency_id
        )

    # ==================== ONCHANGE METODLAR - MALİYET FİYATLARI ====================

    @api.onchange('standard_price', 'supplier_taxes_id')
    def _onchange_standard_price(self):
        """Maliyet fiyatı değişince: vergiler dahil maliyeti ve dövizleri güncelle"""
        if self.standard_price and self.custom_cost_currency_id:
            self.custom_cost_price = self._convert_currency(
                self.standard_price,
                self._get_company_currency(),
                self.custom_cost_currency_id
            )
        
        self.cost_with_tax = self._calculate_tax_on_amount(
            self.standard_price,
            self.supplier_taxes_id
        )
        
        if self.cost_with_tax and self.custom_cost_currency_id:
            self.custom_cost_price_with_tax = self._convert_currency(
                self.cost_with_tax,
                self._get_company_currency(),
                self.custom_cost_currency_id
            )

    @api.onchange('cost_with_tax', 'supplier_taxes_id')
    def _onchange_cost_with_tax(self):
        """Vergiler dahil maliyet değişince: maliyeti ve dövizleri güncelle"""
        self.standard_price = self._remove_tax_from_amount(
            self.cost_with_tax,
            self.supplier_taxes_id
        )
        
        if self.standard_price and self.custom_cost_currency_id:
            self.custom_cost_price = self._convert_currency(
                self.standard_price,
                self._get_company_currency(),
                self.custom_cost_currency_id
            )
        
        if self.cost_with_tax and self.custom_cost_currency_id:
            self.custom_cost_price_with_tax = self._convert_currency(
                self.cost_with_tax,
                self._get_company_currency(),
                self.custom_cost_currency_id
            )

    @api.onchange('custom_cost_price', 'custom_cost_currency_id')
    def _onchange_custom_cost_price(self):
        """Dövizli maliyet değişince: TL'yi ve diğer tüm maliyetleri güncelle"""
        if not self.custom_cost_price or not self.custom_cost_currency_id:
            return
        
        company_currency = self._get_company_currency()
        
        self.standard_price = self._convert_currency(
            self.custom_cost_price,
            self.custom_cost_currency_id,
            company_currency
        )
        
        self.cost_with_tax = self._calculate_tax_on_amount(
            self.standard_price,
            self.supplier_taxes_id
        )
        
        self.custom_cost_price_with_tax = self._convert_currency(
            self.cost_with_tax,
            company_currency,
            self.custom_cost_currency_id
        )

    @api.onchange('custom_cost_price_with_tax', 'custom_cost_currency_id', 'supplier_taxes_id')
    def _onchange_custom_cost_price_with_tax(self):
        """Dövizli vergiler dahil maliyet değişince: hepsini güncelle"""
        if not self.custom_cost_price_with_tax or not self.custom_cost_currency_id:
            return
        
        company_currency = self._get_company_currency()
        
        self.cost_with_tax = self._convert_currency(
            self.custom_cost_price_with_tax,
            self.custom_cost_currency_id,
            company_currency
        )
        
        self.standard_price = self._remove_tax_from_amount(
            self.cost_with_tax,
            self.supplier_taxes_id
        )
        
        self.custom_cost_price = self._convert_currency(
            self.standard_price,
            company_currency,
            self.custom_cost_currency_id
        )

    # ==================== CREATE / WRITE METODLAR ====================

    @api.model
    def create(self, vals_list):
        """Ürün oluştururken default vergileri ayarla"""
        for vals in vals_list:
            if 'taxes_id' not in vals or not vals.get('taxes_id'):
                default_taxes = self._get_default_sales_tax_20_percent()
                if default_taxes:
                    vals['taxes_id'] = [(6, 0, default_taxes)]
            
            if 'supplier_taxes_id' not in vals or not vals.get('supplier_taxes_id'):
                default_taxes = self._get_default_tax_20_percent()
                if default_taxes:
                    vals['supplier_taxes_id'] = [(6, 0, default_taxes)]
        
        return super().create(vals_list)

    def write(self, vals):
        """Ürün güncellenirken default vergileri ayarla"""
        if 'taxes_id' in vals:
            tax_val = vals.get('taxes_id')
            is_empty = not tax_val or (isinstance(tax_val, list) and len(tax_val) == 0)
            if is_empty:
                default_taxes = self._get_default_sales_tax_20_percent()
                if default_taxes:
                    vals['taxes_id'] = [(6, 0, default_taxes)]
        
        if 'supplier_taxes_id' in vals:
            supplier_tax_val = vals.get('supplier_taxes_id')
            is_empty = not supplier_tax_val or (isinstance(supplier_tax_val, list) and len(supplier_tax_val) == 0)
            if is_empty:
                default_taxes = self._get_default_tax_20_percent()
                if default_taxes:
                    vals['supplier_taxes_id'] = [(6, 0, default_taxes)]
        
        return super().write(vals)

    # ==================== DÖNÜŞÜM AKSIYON METODLARI ====================

    def action_convert_döviz_to_tl(self):
        """Döviz fiyatlarını TL'ye dönüştür - satış VE maliyet"""
        for record in self:
            # SATIŞ FİYATLARI DÖNÜŞTÜRME
            if record.custom_list_price and record.custom_currency_id:
                record.list_price = record._convert_currency(
                    record.custom_list_price,
                    record.custom_currency_id,
                    record._get_company_currency()
                )
            record._onchange_list_price()
            
            # MALİYET FİYATLARI DÖNÜŞTÜRME
            if record.custom_cost_price and record.custom_cost_currency_id:
                record.standard_price = record._convert_currency(
                    record.custom_cost_price,
                    record.custom_cost_currency_id,
                    record._get_company_currency()
                )
            record._onchange_standard_price()
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Başarılı',
                'message': f'Dövizden TL\'ye Dönüşüm Tamamlandı ({len(self)} ürün)',
                'type': 'success',
                'sticky': False,
            }
        }

    def action_convert_tl_to_döviz(self):
        """TL fiyatlarını dövize dönüştür - satış VE maliyet"""
        for record in self:
            # SATIŞ FİYATLARI DÖNÜŞTÜRME
            if record.list_price and record.custom_currency_id:
                record.custom_list_price = record._convert_currency(
                    record.list_price,
                    record._get_company_currency(),
                    record.custom_currency_id
                )
            record._onchange_custom_list_price()
            
            # MALİYET FİYATLARI DÖNÜŞTÜRME
            if record.standard_price and record.custom_cost_currency_id:
                record.custom_cost_price = record._convert_currency(
                    record.standard_price,
                    record._get_company_currency(),
                    record.custom_cost_currency_id
                )
            record._onchange_custom_cost_price()
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Başarılı',
                'message': f'TL\'den Dövize Dönüşüm Tamamlandı ({len(self)} ürün)',
                'type': 'success',
                'sticky': False,
            }
        }
