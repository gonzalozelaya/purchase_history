# -*- coding: utf-8 -*-
{
    'name': "Purchase History",

    'summary': """
    
        """,

    'description': """
        
    """,

    'author': "OutsourceArg",
    'website': "https://www.outsourcearg.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/master/odoo/addons/base/module/module_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['purchase','web_studio','purchase_requisition'],

    'data':[
        'views/purchase_history_views.xml',
        'views/purchase_order.xml',
        'security/ir.model.access.csv'
    ]
}