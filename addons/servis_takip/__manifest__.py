{
    'name': 'Servis Yönetimi',
    'version': '19.0.1.0.1',
    'summary': 'Müşteriye ait ürünlerin teknik servis ve onarım süreçlerini takip eder.',
    'description': """
Servis Yönetimi Modülü
======================
Bu modül, müşteri ürünlerinin kabulünden onarımına, yedek parça kullanımından 
teslimatına kadar tüm teknik servis süreçlerini yönetmenizi sağlar.
    """,
    'author': 'DemoProje', 
    'category': 'Services/Field Service',
    'website': 'https://www.demoproje.com', 
    'images': [
        'static/description/icon.png',
    ],
    'depends': [
        'base', 
        'contacts', 
        'hr', 
        'product',   
        'account',
        'mail',
        'sale',  
        'base_setup', 
    ],
    'data': [
        # 1. GÜVENLİK/ACL (Her zaman en başta olmalı)
        'security/ir.model.access.csv', 
        
        # 2. VERİ ve SEQUENCE (Kayıt numaraları için)
        'data/sequences/servis_kaydi_sequence.xml',
        'data/sequences/rapor_sequence.xml',
        
        # 3. VIEWS - TANIMLAR (Definitions)
        'views/definitions/urun_views.xml',
        'views/definitions/servis_urun_views.xml',
        'views/definitions/servis_tanim_views.xml',
        'views/definitions/aksesuar_views.xml',
        'views/definitions/deger_okuma_tanim_views.xml',

        # 3.5. VIEWS - PRODUCT EXTENSIONS (Dövizli Fiyat)
        'views/product_extensions_views.xml',

        # 4. VIEWS - MISC
        'views/misc/urun_popups.xml',
        'views/misc/servis_popups.xml',
        'views/misc/res_config_settings_views.xml',  # Ayarlar

        # 5. VIEWS - CORE (Ana işlemler)
        'views/core/servis_actions.xml',
        'views/core/servis_kaydi_views.xml',
        'views/core/servis_takip_views.xml',

        # 6. VIEWS - RAPORLAR
        'views/reports/kabul_rapor_views.xml',
        'views/reports/teslim_rapor_views.xml',

        # 7. VIEWS - WIZARD'LAR
        'views/wizards/servis_urun_aktar_views.xml',
        'views/wizards/servis_rapor_gonder_wizard_views.xml',
        'views/wizards/servis_ozellestirme_views.xml',  # Özelleştirme
        
        # 8. MENÜLER (En son yüklenmeli çünkü tüm Action ID'leri yukarıda tanımlandı)
        'views/misc/servis_menu.xml',
    ],
    'demo': [
        # 'demo/servis_demo.xml', 
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}

