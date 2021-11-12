from odoo import fields, models, api


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    speciality_ids = fields.Many2many(comodel_name='hr.specialty.tag',
                                      string='Specialities', required=False)
