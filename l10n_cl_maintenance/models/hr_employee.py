from odoo import fields, models, api


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    speciality_id = fields.Many2one(comodel_name='hr.specialty.tag',
                                    string='Speciality', required=False)
