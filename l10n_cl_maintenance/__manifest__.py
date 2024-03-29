# -*- coding: utf-8 -*-

{
    'name': 'Chile - Maintenance',
    'version': '1.0',
    'sequence': 125,
    'category': 'Operations/Maintenance',
    'description': """
Track equipments and maintenance requests
""",
    'depends': ['maintenance', 'uom'],
    'summary': 'Track equipment and manage maintenance requests',
    # 'website': 'https://www.odoo.com/page/tpm-maintenance-software',
    'data': [
        # 'security/maintenance.xml',
        'security/ir.model.access.csv',
        # 'data/maintenance_data.xml',
        # 'data/mail_data.xml',
        'views/maintenance_views.xml',
        # 'views/maintenance_templates.xml',
        # 'views/mail_activity_views.xml',
        # 'data/maintenance_cron.xml',
    ],
    # 'demo': ['data/maintenance_demo.xml'],
    'installable': True,
    # 'application': True,
}
