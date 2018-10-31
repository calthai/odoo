# -*- coding: utf-8 -*-
# Copyright (C) 2016-Today  ITAAS (<http://www.itaas.co.th/>).
{
    "name": "Capelda Extended",
    "category": 'General',
    'summary': 'This is Capelda Project',
    "description": """
        .
    """,
    "sequence": 1,
    "author": "IT as a Service Co., Ltd.",
    "website": "http://www.itaas.co.th/",
    "version": '1.0',
    "depends": ['stock'],
    "data": [
        'views/stock_picking_view.xml',
        'views/stock_location_view.xml',
        'views/product_template_view.xml',
        'views/stock_receipts_export.xml',
    ],
    'qweb': [],
    "installable": True,
    "application": True,
    "auto_install": False,
}