# -*- coding: utf-8 -*-

{
    'name': 'MBLZ: Chile - Maintenance',
    'version': '1.0',
    'sequence': 125,
    'category': 'Operations/Maintenance',
    'description': """
        Seguimiento de los equipos y de las solicitudes de mantenimiento
    """,
    'summary': 'Seguimiento de los equipos y gestión de las solicitudes de mantenimiento',
    'website': "https://www.mobilize.cl",
    'depends': ['maintenance', 'uom', 'hr'],

    'data': [
        # 'security/maintenance.xml',
        'security/ir.model.access.csv',

        'data/sequences.xml',

        # 'data/maintenance_data.xml',
        # 'data/mail_data.xml',
        'views/templates.xml',
        'views/hr_speciality_tag.xml',
        'views/guideline_activity.xml',
        'views/hr_employee.xml',

        'views/maintenance_guideline.xml',
        'views/maintenance_equipment.xml',
        # 'views/maintenance_equipment_activity.xml',

        'views/maintenance_request.xml',

        'wizard/guideline_line_confirm.xml',

        # menu
        'menus/guideline.xml',

        # 'views/maintenance_templates.xml',
        # 'views/mail_activity_views.xml',

        # 'data/maintenance_cron.xml',

    ],
    # 'demo': ['data/maintenance_demo.xml'],
    'images': ['static/description/icon.png'],

    'installable': True,
    'auto_install': False,
    'application': True,
    'license': 'AGPL-3',
}
