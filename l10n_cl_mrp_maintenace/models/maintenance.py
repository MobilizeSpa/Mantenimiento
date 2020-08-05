# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class MaintenanceGuideline(models.Model):
    _inherit = 'maintenance.guideline'

    bom_id = fields.Many2one('mrp.bom', 'Bill of Material', check_company=True,
        domain="[('type', '=', 'normal'), '|', ('company_id', '=', False), ('company_id', '=', company_id)]",
        help="Bill of Materials allow you to define the list of required components to make a maintenance."
        )


class MaintenanceRequest(models.Model):
    _inherit = 'maintenance.request'

    @api.model
    def _default_warehouse_id(self):
        company = self.env.company.id
        warehouse_ids = self.env['stock.warehouse'].search([('company_id', '=', company)], limit=1)
        return warehouse_ids

    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse', required=True, readonly=True,
        default=_default_warehouse_id, check_company=True
        )
    bom_id = fields.Many2one('mrp.bom', 'Bill of Material',
        related="maintenance_guideline_id.bom_id"
        )
