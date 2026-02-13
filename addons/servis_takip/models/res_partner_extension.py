from odoo import models, fields, api
from datetime import datetime
import logging

_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    _inherit = 'res.partner'

    cari_kod = fields.Char(
        string='Cari Kod',
        help='Müşteri/Tedarikçi cari kod (YYYYNNNN formatı)',
        readonly=False
    )

    @api.model
    def default_get(self, fields_list):
        """Form açılırken default cari kodu ata"""
        res = super().default_get(fields_list)
        if 'cari_kod' in fields_list:
            res['cari_kod'] = self._get_next_cari_kod()
        return res

    @api.model
    def _get_next_cari_kod(self):
        """Son cari koda bakarak yeni cari kodu oluştur"""
        current_year = datetime.now().year
        
        try:
            # Tüm kontaktları cari_kod'a göre al
            all_partners = self.search([('cari_kod', '!=', False)])
            
            if all_partners:
                # Son kontağı bul (cari_kod'a göre ters sırala)
                sorted_partners = sorted(all_partners, key=lambda x: x.cari_kod or '', reverse=True)
                last_partner = sorted_partners[0]
                last_code = last_partner.cari_kod.strip() if last_partner.cari_kod else None
                
                if last_code and len(last_code) >= 8 and last_code[:4].isdigit() and last_code[4:].isdigit():
                    last_year = int(last_code[:4])
                    last_sequence = int(last_code[4:])
                    
                    # Eğer son kayıt bu yılsa +1 yap
                    if last_year == current_year:
                        next_sequence = last_sequence + 1
                        return f"{current_year}{next_sequence:04d}"
                    # Eğer geçmiş yılussa bu yıldan başla
                    else:
                        return f"{current_year}0001"
                else:
                    # Format hata, yeni formatla başla
                    return f"{current_year}0001"
            else:
                # Hiç cari kod yoksa bu yıldan başla
                return f"{current_year}0001"
                
        except Exception as e:
            _logger.warning(f"Cari kod oluşturma hatası: {str(e)}")
            return f"{current_year}0001"

    def create(self, vals_list):
        """Yeni kontakt oluştururken cari kodu otomatik ata"""
        try:
            # Odoo 19: vals_list bir liste olmalı
            if isinstance(vals_list, dict):
                # Eğer tek dict gelmişse, listeye çevir
                vals_list = [vals_list]
            
            for vals in vals_list:
                # Eğer cari kod boşsa, otomatik ata
                if isinstance(vals, dict) and not vals.get('cari_kod'):
                    vals['cari_kod'] = self._get_next_cari_kod()
            
            return super().create(vals_list)
        except Exception as e:
            _logger.error(f"create() hatası: {str(e)}")
            # Hata durumunda yine de oluştursun
            return super().create(vals_list)

