# -*- encoding: utf-8 -*-
{
    'name': 'MBLZ: Chile - Maintenance MRP',
    'version': '1.0',
    'category': 'Manufacturing/Manufacturing',
    'summary': 'Programe y gestione el mantenimiento de máquinas y herramientas.',
    'website': "https://www.mobilize.cl",

    'description': """
        Solicitar lista de materiales para un mantenimiento ...
    """,

    'depends': ['mrp_maintenance', 'l10n_cl_maintenance'],
    'data': [
        # 'security/ir.model.access.csv',
        'data/maintenance_data.xml',
        'views/maintenance_views.xml',
    ],
    # 'demo': ['data/mrp_maintenance_demo.xml'],
    'images': ['static/description/icon.png'],

    'installable': True,
    'auto_install': True,
    'application': True,
    'license': 'AGPL-3',
}
# Part of Odoo. See LICENSE file for full copyright and licensing details.
