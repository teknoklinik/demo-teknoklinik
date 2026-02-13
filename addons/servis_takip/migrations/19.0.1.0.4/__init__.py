# Migration: Add cari_kod field to res_partner
# -*- coding: utf-8 -*-


def migrate(cr, version):
    """Add cari_kod column to res_partner table if it doesn't exist"""
    cr.execute("""
        ALTER TABLE res_partner 
        ADD COLUMN IF NOT EXISTS cari_kod VARCHAR
    """)
