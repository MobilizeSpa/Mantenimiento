# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, Warning


class MaintenanceEquipmentActivity(models.Model):
    _name = 'maintenance.equipment.activity'
    _description = 'Maintenance Equipment Activity'

    name = fields.Char('Name', required=True)
    uom_id = fields.Many2one('uom.uom', 'Unit of Measure', required=True)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)

    equipment_ids = fields.One2many('maintenance.equipment', compute='_compute_equipment_data', string='Equipments')
    equipment_count = fields.Integer(string='Equipment', compute='_compute_equipment_data')
    maintenance_ids = fields.One2many('maintenance.request', compute='_compute_equipment_data')
    maintenance_count = fields.Integer(string="Maintenance Count", compute='_compute_equipment_data')

    def _compute_equipment_data(self):
        self.ensure_one()

        equipments = self.env['maintenance.guideline'].search([
            ('company_id', 'in', (self.company_id.id, False)),
            ('equipment_activity_id', '=', self.id),
        ]).mapped('equipment_id')
        equipments += self.env['maintenance.equipment.activity.tracking'].search([
            ('company_id', 'in', (self.company_id.id, False)),
            ('equipment_activity_id', '=', self.id),
        ]).mapped('equipment_id')

        self.equipment_count = len(equipments)
        self.equipment_ids = equipments
        self.maintenance_ids = equipments.mapped('maintenance_ids')
        self.maintenance_count = len(self.maintenance_ids.filtered(lambda x: not x.stage_id.done))
