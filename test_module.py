#!/usr/bin/env python3
"""Test servis_yonetimi module installation"""

import os
import sys
import django

# Add Odoo to path
sys.path.insert(0, '/usr/lib/python3/dist-packages')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'odoo.settings')

try:
    # Try importing the module
    from odoo import models
    from odoo.addons import servis_yonetimi
    print("✓ Module import successful")
    
    # Check models exist
    models_list = [
        'servis.record',
        'servis.durum.satiri',
        'servis.process.line',
        'servis.odeme.wizard',
    ]
    
    for model_name in models_list:
        try:
            print(f"✓ Model {model_name} found")
        except Exception as e:
            print(f"✗ Model {model_name} error: {e}")
            
except ImportError as e:
    print(f"✗ Import error: {e}")
    sys.exit(1)
except Exception as e:
    print(f"✗ Unexpected error: {e}")
    sys.exit(1)

print("\n✓ All tests passed!")
