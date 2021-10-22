# -*- coding: utf-8 -*-
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from odoo.tools import float_is_zero


class MaintenanceStage(models.Model):
    _inherit = 'maintenance.stage'

    request_bom = fields.Boolean("Request Bill of Material")
    require_bom = fields.Boolean("Require Bill of Material")


class MaintenanceGuideline(models.Model):
    _inherit = 'maintenance.guideline'

    bom_id = fields.Many2one('mrp.bom', 'Bill of Material', check_company=True,
                             domain="[('type', '=', 'normal'), '|', ('company_id', '=', False), ('company_id', '=', company_id)]",
                             help="Bill of Materials allow you to define the list of required components to make a maintenance."
                             )


class MaintenanceTeam(models.Model):
    _inherit = 'maintenance.team'

    maintenance_location_id = fields.Many2one("stock.location", "Maintenance Location",
                                              domain="['|', ('company_id', '=', company_id), ('company_id', '=', False), ('usage', 'in', ['production', 'customer'])]"
                                              )


class MaintenanceRequest(models.Model):
    _inherit = 'maintenance.request'

    @api.model
    def _default_warehouse_id(self):
        company = self.env.company.id
        warehouse_ids = self.env['stock.warehouse'].search([('company_id', '=', company)], limit=1)
        return warehouse_ids

    @api.model
    def _default_maintenance_location(self):
        Location = self.env['stock.location']

        team = self.env['maintenance.team'].browse(self._get_default_team_id())
        maintenance_location = team.maintenance_location_id

        if not maintenance_location:
            maintenance_location = Location.search([
                ('usage', 'in', ['production', 'customer']),
                '|', ('company_id', '=', self.env.company.id),
                ('company_id', '=', False),
            ], limit=1)

        return maintenance_location

    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse', required=True, readonly=True,
                                   default=_default_warehouse_id, check_company=True
                                   )
    bom_id = fields.Many2one('mrp.bom', 'Bill of Material',
                             related="maintenance_guideline_id.bom_id"
                             )
    maintenance_location_id = fields.Many2one("stock.location", "Maintenance Location", check_company=True,
                                              domain="['|', ('company_id', '=', company_id), ('company_id', '=', False), ('usage', 'in', ['production', 'customer'])]",
                                              default=_default_maintenance_location
                                              )
    procurement_group_id = fields.Many2one('procurement.group', 'Procurement Group', copy=False)
    picking_ids = fields.One2many('stock.picking', 'maintenance_id', string='Transfers')
    picking_count = fields.Integer(string='BoM Transfers', compute='_compute_picking_count')

    @api.depends('picking_ids')
    def _compute_picking_count(self):
        for request in self:
            request.picking_count = len(request.picking_ids.filtered(
                lambda p: p.location_dest_id == request.maintenance_location_id)
            )

    @api.onchange('maintenance_team_id')
    def _onchange_maintenance_team(self):
        if self.maintenance_team_id and not self.maintenance_location_id:
            self.maintenance_location_id = self.maintenance_team_id.maintenance_location_id

    @api.constrains("stage_id")
    def _check_bom_stage(self):
        bom_request_without_done_pickings = self.filtered(
            lambda r: r.stage_id.require_bom and (
                    not r.picking_ids or any(p.state != 'done'
                                             for p in r.picking_ids
                                             if p.location_dest_id == r.maintenance_location_id)
            )
        )

        if bom_request_without_done_pickings:
            raise ValidationError(_(
                "The following %s %s need a processed Bill of Material transfer request in order to continue"
            ) % (
                                      _(self._description),
                                      ', '.join(bom_request_without_done_pickings.mapped('display_name')),
                                  ))

        self.filtered(lambda r: r.stage_id.request_bom and not r.picking_ids)._action_launch_stock_rule()

    def action_view_delivery_bom(self):
        """
        This function returns an action that display existing delivery bom orders
        of given maintenance request ids. It can either be a in a list or in a form
        view, if there is only one delivery bom order to show.
        """
        action = self.env.ref('stock.action_picking_tree_all').read()[0]

        pickings = self.mapped('picking_ids').filtered(
            lambda p: p.location_dest_id == p.group_id.maintenance_id.maintenance_location_id
        )
        if len(pickings) > 1:
            action['domain'] = [('id', 'in', pickings.ids)]
        elif pickings:
            form_view = [(self.env.ref('stock.view_picking_form').id, 'form')]
            if 'views' in action:
                action['views'] = form_view + [(state, view) for state, view in action['views'] if view != 'form']
            else:
                action['views'] = form_view
            action['res_id'] = pickings.id

        # Prepare the context.
        picking_id = pickings.filtered(lambda l: l.picking_type_id.code == 'outgoing')
        if picking_id:
            picking_id = picking_id[0]
        else:
            picking_id = pickings[0]

        action['context'] = dict(
            self._context,
            default_picking_id=picking_id.id,
            default_picking_type_id=picking_id.picking_type_id.id,
            default_origin=self.name,
            default_group_id=picking_id.group_id.id
        )

        return action

    def _action_launch_stock_rule(self):
        """
        Launch procurement group run method with required/custom fields genrated by a
        maintenance request. procurement group will launch '_run_pull', '_run_buy' or '_run_manufacture'
        depending on the maintenance request bom line product rule.
        """
        precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')
        procurements = []
        nonactive_test = False

        for request in self:
            if not request.bom_id or not all(
                    line.product_id.type in ('consu', 'product') for line in request.bom_id.bom_line_ids):
                continue

            for line in request.bom_id.bom_line_ids:
                qty = line.product_qty
                if float_is_zero(qty, precision_digits=precision):
                    continue

                group_id = request.procurement_group_id
                if not group_id:
                    group_id = self.env['procurement.group'].create(request._prepare_procurement_group_vals())
                    request.procurement_group_id = group_id
                else:
                    # In case the procurement group is already created and the request was
                    # cancelled, we need to update certain values of the group.
                    updated_vals = {}
                    # if group_id.partner_id != line.order_id.partner_shipping_id:
                    #     updated_vals.update({'partner_id': line.order_id.partner_shipping_id.id})
                    if group_id.move_type != 'one':
                        updated_vals.update({'move_type': 'one'})
                    if updated_vals:
                        group_id.write(updated_vals)

                values = request._prepare_procurement_values(line, group_id=group_id)

                # nonactive_test = nonactive_test or bool(self.maintenance_location_id and
                #                                     self.maintenance_location_id.usage == 'production' and
                #                                     self.warehouse_id)

                procurements.append(self.env['procurement.group'].Procurement(
                    line.product_id,
                    qty,
                    line.product_uom_id,
                    request.maintenance_location_id,
                    line.display_name,
                    request.name,
                    request.company_id,
                    values
                ))
        if procurements:
            self.env['procurement.group'].with_context(active_test=not nonactive_test).run(procurements)

        return True

    def _prepare_procurement_group_vals(self):
        return {
            'maintenance_id': self.id,
            'name': self.name,
            'move_type': 'one',
            # 'partner_id': self.order_id.partner_shipping_id.id,
        }

    def _prepare_procurement_values(self, line, group_id=False):
        """ Prepare specific key for moves or other components that will be created from a stock rule
        comming from a sale order line. This method could be override in order to add other custom key that could
        be used in move/po creation.
        """
        self.ensure_one()
        date_planned = self.schedule_date

        values = {
            'warehouse_id': self.warehouse_id or False,
            'company_id': self.company_id,
            'date_planned': date_planned,
            # 'route_ids': self.route_id,
            'maintenance_id': self.id,
            'group_id': group_id,
        }

        # if self.maintenance_location_id and self.maintenance_location_id.usage == 'production' and self.warehouse_id:
        #     values.update(route_ids=self.warehouse_id._find_global_route('l10n_cl_mrp_maintenance.route_warehouse0_bom', _('Pickup BoM')))

        return values


class MaintenanceEquipment(models.Model):
    _inherit = 'maintenance.equipment'

    mbfm_custom = fields.Selection(
        [('hours', 'Hours'), ('days', 'Days')],
        string='MTBF Metric', default="days",
        help='Mean Time Between Failure Measure')

    def _register_hook(self):
        """ Patch models to correct the that should trigger """

        def make__compute_maintenance_request():
            """ Instanciate the _compute_maintenance_request. """

            @api.depends('mbfm_custom')
            def _compute_maintenance_request(self):
                for equipment in self:
                    maintenance_requests = equipment.maintenance_ids.filtered(
                        lambda x: x.maintenance_type == 'corrective' and x.stage_id.done
                    )
                    mttr_days_factor = 1 if equipment.mbfm_custom == 'days' else 24
                    mttr_days = 0

                    for maintenance in maintenance_requests:
                        if maintenance.stage_id.done and maintenance.close_date:
                            mttr_days += (maintenance.close_date - maintenance.request_date).days * mttr_days_factor

                    equipment.mttr = len(maintenance_requests) and (mttr_days / len(maintenance_requests)) or 0

                    maintenance = maintenance_requests.sorted(lambda x: x.request_date)

                    if len(maintenance) >= 1:
                        equipment.mtbf = (maintenance[
                                              -1].request_date - equipment.effective_date).days * mttr_days_factor / len(
                            maintenance)

                    equipment.latest_failure_date = maintenance and maintenance[-1].request_date or False

                    if equipment.mtbf:
                        if equipment.mbfm_custom == 'days':
                            equipment.estimated_next_failure = equipment.latest_failure_date + relativedelta(
                                days=equipment.mtbf)
                        else:
                            equipment.estimated_next_failure = equipment.latest_failure_date + relativedelta(
                                hours=equipment.mtbf)
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
