# -*- coding: utf-8 -*-
from dateutil.relativedelta import relativedelta

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


class MaintenanceEquipment(models.Model):
    _inherit = 'maintenance.equipment'

    mbfm = fields.Selection([('hours', 'Hours'), ('days', 'Days')], string='MTBF Metric', default="days",
        help='Mean Time Between Failure Measure'
        )

    def _register_hook(self):
        """ Patch models to correct the that should trigger """

        def make__compute_maintenance_request():
            """ Instanciate the _compute_maintenance_request. """

            @api.depends('mbfm')
            def _compute_maintenance_request(self):
                for equipment in self:
                    maintenance_requests = equipment.maintenance_ids.filtered(
                                                lambda x: x.maintenance_type == 'corrective' and x.stage_id.done
                                                )
                    mttr_days_factor = 1 if equipment.mbfm == 'days' else 24
                    mttr_days = 0

                    for maintenance in maintenance_requests:
                        if maintenance.stage_id.done and maintenance.close_date:
                            mttr_days += (maintenance.close_date - maintenance.request_date).days * mttr_days_factor

                    equipment.mttr = len(maintenance_requests) and (mttr_days / len(maintenance_requests)) or 0

                    maintenance = maintenance_requests.sorted(lambda x: x.request_date)

                    if len(maintenance) >= 1:
                        equipment.mtbf = (maintenance[-1].request_date - equipment.effective_date).days * mttr_days_factor / len(maintenance)

                    equipment.latest_failure_date = maintenance and maintenance[-1].request_date or False

                    if equipment.mtbf:
                        if equipment.mbfm == 'days':
                            equipment.estimated_next_failure = equipment.latest_failure_date + relativedelta(days=equipment.mtbf)
                        else:
                            equipment.estimated_next_failure = equipment.latest_failure_date + relativedelta(hours=equipment.mtbf)
                    else:
                        equipment.estimated_next_failure = False

            return _compute_maintenance_request

        bases = type(self).mro()
        bases.reverse()
        make_patched_methods = [(method_name[5:], method_patch)
                                for method_name, method_patch in locals().items()
                                if 'make_' in method_name]

        for base in bases:
            if hasattr(base, '_name') and base._name == self._name:
                methods_2patch = [(method_name, method_patch)
                                  for method_name, method_patch in make_patched_methods
                                  if hasattr(base, method_name)]

                for method_name, method_patch in methods_2patch:
                    base._patch_method(method_name, method_patch())
                    patched_method = getattr(base, method_name)
                    patched_method.origin_base = base
                    # mark the method as patched
                    make_patched_methods.remove((method_name, method_patch))

            if not make_patched_methods:
                break

        super(MaintenanceEquipment, self)._register_hook()
