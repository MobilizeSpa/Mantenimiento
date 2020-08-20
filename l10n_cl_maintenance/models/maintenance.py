# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


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


class MaintenanceGuidelineType(models.Model):
    _name = 'maintenance.guideline.type'
    _description = 'Maintenance Guideline Type'

    name = fields.Char('Name', required=True)
    prefix = fields.Char(help="Prefix value of the record for Maintenance Guideline", trim=False)
    suffix = fields.Char(help="Suffix value of the record for Maintenance Guideline", trim=False)
    preview = fields.Char(compute='_compute_preview')
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)

    @api.depends('name', 'prefix', 'suffix')
    def _compute_preview(self):
        for record in self:
            record.preview = ("%s xxxx yyyy" % ' '.join(filter(None, [
                                                        record.prefix or '',
                                                        record.name or '',
                                                        record.suffix or ''
                                                        ]))).strip()


class MaintenanceGuideline(models.Model):
    _name = 'maintenance.guideline'
    _description = 'Maintenance Guideline'

    _check_company_auto = True

    name = fields.Char('Name', compute='_compute_name', readonly=True, store=True)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    description = fields.Text('Description')
    guideline_type_id = fields.Many2one('maintenance.guideline.type', 'Guideline Type', ondelete='restrict',
        required=True, check_company=True
        )
    maintenance_duration = fields.Float(help="Maintenance Duration in hours.")

    equipment_id = fields.Many2one('maintenance.equipment', string='Equipment', ondelete='cascade', index=True,
        check_company=True)
    equipment_activity_id = fields.Many2one('maintenance.equipment.activity', 'Equipment Activity', required=True,
        check_company=True)
    equipment_activity_uomctg_id = fields.Many2one('uom.category', 'Equipment Activity UoM Category',
        related='equipment_activity_id.uom_id.category_id', readonly=True,
        store=True
        )
    uom_id = fields.Many2one('uom.uom', 'Unit of Measure', domain="[('category_id', '=', equipment_activity_uomctg_id)]")

    measurement = fields.Selection([
        ('fixed', 'At reached value'),
        ('frequently', 'Frequently'),
        ], 'Measurement', default='frequently')
    period = fields.Integer('Frequency between each preventive maintenance')
    value = fields.Integer('Value for preventive maintenance')

    @api.depends('guideline_type_id', 'uom_id', 'measurement', 'period', 'value')
    def _compute_name(self):
        for record in self:
            record.name = ('%s %s %s' % (
                            ' '.join(filter(None, [
                                record.guideline_type_id.prefix or '',
                                record.guideline_type_id.name or '',
                                record.guideline_type_id.suffix or '',
                                ])),
                            record.period if record.measurement == 'frequently' else record.value ,
                            record.uom_id.name or '',
                            )).strip()

    @api.onchange('equipment_activity_id')
    def _onchange_equipment_activity(self):
        if self.equipment_activity_id:
            self.uom_id = self.equipment_activity_id.uom_id

    @api.onchange('measurement')
    def _onchange_measurement(self):
        if self.measurement == 'frequently':
            self.value = False
        else:
            self.period = False

    @api.constrains('period', 'value')
    def _check_maintenance_measurement(self):
        invalid_records = self.filtered(lambda r: not r.period and not r.value)

        if invalid_records:
            raise ValidationError(_(
                "The following %s %s don't have value either for frequently or fixed measurement"
                ) % (
                ',\n '.join(invalid_records.mapped('display_name')),
                _(self._description),
                ))

    @api.constrains('uom_id', 'equipment_activity_uomctg_id')
    def _check_uom_category(self):
        invalid_records = self.filtered(lambda r: r.uom_id.category_id != r.equipment_activity_uomctg_id)
        if invalid_records:
            raise ValidationError(_(
                "The following %s %s don't have the correct unit of measurement category"
                ) % (
                ',\n '.join(invalid_records.mapped('display_name')),
                _(self._description),
                ))


class MaintenanceEquipmentActivityTracking(models.Model):
    _name = 'maintenance.equipment.activity.tracking'
    _description = 'Maintenance Equipment Activity Tracking'

    _check_company_auto = True

    name = fields.Char('Name', required=True)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    equipment_id = fields.Many2one('maintenance.equipment', string='Equipment', ondelete='cascade', index=True,
        check_company=True)
    equipment_activity_id = fields.Many2one('maintenance.equipment.activity', 'Equipment Activity', required=True,
        check_company=True)
    equipment_activity_uomctg_id = fields.Many2one('uom.category', 'Equipment Activity UoM Category',
        related='equipment_activity_id.uom_id.category_id', readonly=True,
        store=True
        )
    uom_id = fields.Many2one('uom.uom', 'Unit of Measure', domain="[('category_id', '=', equipment_activity_uomctg_id)]")
    tracking_date = fields.Datetime('Tracking Date', default=fields.Datetime.now)
    tracking_value = fields.Integer('Tracking Value')
    tracking_eauom_value = fields.Integer('Tracking Value on Equipment Actv UoM',
        compute='_compute_tracking_eauom_value', store=True
        )

    @api.depends('equipment_activity_uomctg_id', 'uom_id', 'tracking_value')
    def _compute_tracking_eauom_value(self):
        for record in self:
            record.tracking_eauom_value = record.uom_id._compute_quantity(
                                                            record.tracking_value,
                                                            record.equipment_activity_id.uom_id
                                                            )

    @api.onchange('equipment_activity_id')
    def _onchange_equipment_activity(self):
        if self.equipment_activity_id:
            self.uom_id = self.equipment_activity_id.uom_id

    @api.constrains('uom_id', 'equipment_activity_uomctg_id')
    def _check_uom_category(self):
        invalid_records = self.filtered(lambda r: r.uom_id.category_id != r.equipment_activity_uomctg_id)

        if invalid_records:
            raise ValidationError(_(
                "The following %s %s does not have the correct unit of measurement category"
                ) % (
                ',\n '.join(invalid_records.mapped('display_name')),
                _(self._description),
                ))


class MaintenanceEquipment(models.Model):
    _inherit = 'maintenance.equipment'

    maintenance_guideline_ids = fields.One2many('maintenance.guideline', 'equipment_id',
        'Guideline Of Maintenances'
        )
    maintenance_actv_tracking_ids = fields.One2many('maintenance.equipment.activity.tracking', 'equipment_id',
        'Activity Tracking'
        )
    maintenance_actv_tracking_count = fields.Integer('Activity Tracking Count',
        compute="_compute_maintenance_actv_tracking_count"
        )
    equipment_activity_id = fields.Many2one('maintenance.equipment.activity', 'Equipment Activity',
        related="maintenance_guideline_ids.equipment_activity_id"
        )

    @api.depends('maintenance_actv_tracking_ids')
    def _compute_maintenance_actv_tracking_count(self):
        actv_tracking_data = self.env['maintenance.equipment.activity.tracking'].read_group([
            ('equipment_id', 'in', self.ids),
            ], ['equipment_id'], ['equipment_id'])

        result = dict((data['equipment_id'][0], data['equipment_id_count']) for data in actv_tracking_data)

        for equipment in self:
            equipment.maintenance_actv_tracking_count = result.get(equipment.id, 0)

    @api.model
    def _prepare_request_values(self, date):
        guideline = self.env['maintenance.guideline'].browse(self._context.get('default_maintenance_guideline_id'))

        values = {
            'name': _('Preventive Maintenance - %s') % self.name if not guideline.name else '%s - %s' % (guideline.name, self.name),
            'duration': guideline.maintenance_duration or self.maintenance_duration,
            'company_id': self.company_id.id or self.env.company.id,
            'user_id': self.technician_user_id.id,
            'category_id': self.category_id.id,
            'maintenance_type': 'preventive',
            'equipment_id': self.id,
            'schedule_date': date,
            'request_date': date,
            }

        if self.maintenance_team_id:
            values.update(maintenance_team_id=self.maintenace_team_id.id)
        if self.owner_user_id:
            values.update(owner_user_id=self.owner_user_id.id)

        return values

    def _register_hook(self):
        """ Patch models to correct the that should trigger action rules based on creation,
            modification, deletion of records and form onchanges.
        """

        def make__compute_next_maintenance():
            """ Instanciate the _compute_next_maintenance. """

            @api.depends('effective_date', 'period', 'maintenance_ids.request_date', 'maintenance_ids.close_date')
            def _compute_next_maintenance(self):
                date_now = fields.Date.context_today(self)
                equipments = self.filtered(lambda x: any(mg.period > 0 or mg.value > 0
                                                         for mg in x.maintenance_guideline_ids))

                for equipment in equipments:
                    next_maintenance_todo = self.env['maintenance.request'].search([
                                                    ('equipment_id', '=', equipment.id),
                                                    ('maintenance_type', '=', 'preventive'),
                                                    ('stage_id.done', '!=', True),
                                                    ('close_date', '=', False),
                                                    ], order="request_date asc", limit=1)
                    if next_maintenance_todo:
                        next_date = next_maintenance_todo.request_date
                        # If the new date still in the past, we set it for today
                        if next_date < date_now:
                            next_date = date_now
                    else:
                        next_date = False
                    equipment.next_action_date = next_date

                (self - equipments).next_action_date = False

            return _compute_next_maintenance

        def make__create_new_request():
            def _create_new_request(self, date):
                self.ensure_one()
                self.env['maintenance.request'].create(self._prepare_request_values(date))

            return _create_new_request

        def make__cron_generate_requests():
            """ Instanciate the _compute_next_maintenance. """

            @api.model
            def _cron_generate_requests(self):
                """
                    Generates maintenance request on the next_action_date or today if none exists
                """
                TrackingSudo = self.env['maintenance.equipment.activity.tracking'].sudo()
                today = fields.Date.context_today(self)
                tracking_value_delta = 3

                for guideline in self.env['maintenance.guideline'].search(['|', ('period', '>', 0), ('value', '>', 0)]):
                    equipment = guideline.equipment_id

                    next_requests = self.env['maintenance.request'].search([
                        ('request_date', '=', equipment.next_action_date),
                        ('maintenance_guideline_id', '=', guideline.id),
                        ('equipment_id', '=', equipment.id),
                        ('maintenance_type', '=', 'preventive'),
                        ('stage_id.done', '=', False),
                        ])

                    if not next_requests:
                        tracking_data = TrackingSudo.read_group([
                                        ('equipment_activity_id', '=', guideline.equipment_activity_id.id),
                                        ('equipment_id', '=', equipment.id),
                                        ], ['equipment_activity_id', 'tracking_eauom_value'], 'tracking_eauom_value')
                        tracking_value = tracking_data[0]['tracking_eauom_value']

                        if guideline.measurement == 'frequently':
                            tracking_limit_low = guideline.value - tracking_value_delta
                            tracking_limit_hight = tracking_value_delta
                            tracking_value %= guideline.period
                            if tracking_limit_hight < tracking_value < tracking_limit_low:
                                continue
                        else:
                            tracking_limit_hight = guideline.value + tracking_value_delta
                            tracking_limit_low = guideline.value - tracking_value_delta
                            if not tracking_limit_low <= tracking_value <= tracking_limit_hight:
                                continue

                        equipment.with_context(default_maintenance_guideline_id=guideline.id)._create_new_request(today)

            return _cron_generate_requests

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


class MaintenanceRequest(models.Model):
    _inherit = 'maintenance.request'

    maintenance_guideline_id = fields.Many2one('maintenance.guideline',  'Guideline Of Maintenance',
        domain="[('equipment_id', '=', equipment_id)]", check_company=True
        )
    equipment_activity_id = fields.Many2one('maintenance.equipment.activity', 'Equipment Activity',
        related="maintenance_guideline_id.equipment_activity_id"
        )
