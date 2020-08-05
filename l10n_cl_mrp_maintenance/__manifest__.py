# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Chile - Maintenance MRP',
    'version': '1.0',
    'category': 'Manufacturing/Manufacturing',
    'summary': 'Schedule and manage maintenance on machine and tools.',
    # 'website': 'https://www.odoo.com/page/tpm-maintenance-software',
    'description': """
Request BoM for a Maintenance ...
""",
    'depends': ['mrp_maintenance', 'l10n_cl_maintenance'],
    'data': [
        'views/maintenance_views.xml',
        ],
    # 'demo': ['data/mrp_maintenance_demo.xml'],
    'auto_install': True,
    # 'license': 'OEEL-1',
}
