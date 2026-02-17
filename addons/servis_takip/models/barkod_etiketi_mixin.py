from odoo import models, fields, api
import logging
from io import BytesIO
import base64

_logger = logging.getLogger(__name__)

class BarkodEtiketiMixin(models.AbstractModel):
    _name = 'barkod.etiketi.mixin'
    _description = 'Barkod Etiketi Mixin'

    def get_barcode_base64(self):
        """Seri numarasından base64 formatında barkod oluşturur"""
        if not hasattr(self, 'seri_no') or not self.seri_no:
            return None
        
        try:
            import barcode
            from barcode.writer import ImageWriter # SVG yerine ImageWriter kullanıyoruz
            
            # Barkod üretimi
            # 'code128' genellikle seri numaraları için en uygunudur
            CODE = barcode.get_barcode_class('code128')
            
            # Görsel yazıcı ayarları
            writer = ImageWriter()
            barcode_instance = CODE(self.seri_no, writer=writer)
            
            output = BytesIO()
            # Barkodun altındaki yazıyı ImageWriter eklemesin diye 'display_value': False
            barcode_instance.write(output, options={
                'module_height': 18.0,
                'module_width': 0.4,
                'quiet_zone': 1.0,
                'display_value': False,
                'format': 'PNG'
            })
            
            return base64.b64encode(output.getvalue()).decode('utf-8')
        except Exception as e:
            _logger.warning(f"Barkod üretim hatası: {str(e)}")
            return None