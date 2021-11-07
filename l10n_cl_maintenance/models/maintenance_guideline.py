# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, Warning


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
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Maintenance Guideline General'
    _check_company_auto = True

    name = fields.Char('Name', compute='_compute_name', readonly=True, store=True)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    description = fields.Text('Description')
    guideline_type_id = fields.Many2one('maintenance.guideline.type',
                                        'Guideline Type', ondelete='restrict',
                                        required=True, check_company=True)

    maintenance_type = fields.Selection(
        string=' Maintenance type',
        selection=[('preventive', 'Preventive'),
                   ('corrective', 'Corrective'), ],
        required=True, default='preventive')

    maintenance_duration = fields.Float(help="Maintenance Duration in hours.")

    equipment_id = fields.Many2one('maintenance.equipment', string='Equipment', ondelete='cascade', index=True,
                                   check_company=True)
    equipment_activity_id = fields.Many2one('maintenance.equipment.activity', 'Equipment Activity', required=True,
                                            check_company=True)
    equipment_activity_uomctg_id = fields.Many2one('uom.category', 'Equipment Activity UoM Category',
                                                   related='equipment_activity_id.uom_id.category_id',
                                                   readonly=True, store=True)
    uom_id = fields.Many2one('uom.uom', 'Unit of Measure',
                             domain="[('category_id', '=', equipment_activity_uomctg_id)]")

    measurement = fields.Selection([
        ('fixed', 'At reached value'),
        ('frequently', 'Frequently'),
    ], 'Measurement', default='frequently')
    period = fields.Integer('Frequency between each preventive maintenance')
    value = fields.Integer('Value for preventive maintenance')

    att_documents = fields.Many2many('ir.attachment', string='Documents', required=False)
    url_ids = fields.One2many('guideline.url', 'guideline_id', 'Urls', copy=True, auto_join=True)

    activities_ids = fields.One2many('maintenance.guideline.activity', 'guideline_id', 'Activities', copy=True,
                                     auto_join=True)

    @api.depends('guideline_type_id', 'uom_id', 'measurement', 'period', 'value')
    def _compute_name(self):
        for record in self:
            record.name = ('%s %s %s' % (
                ' '.join(filter(None, [
                    record.guideline_type_id.prefix or '',
                    record.guideline_type_id.name or '',
                    record.guideline_type_id.suffix or '',
                ])),
                record.period if record.measurement == 'frequently' else record.value,
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


class ActivityUrl(models.Model):
    _name = 'guideline.url'

    guideline_id = fields.Many2one('maintenance.guideline', string='Guideline', required=True, ondelete='cascade',
                                   index=True, copy=False)
    name = fields.Char(string='Name', required=True)
    description = fields.Char(string='Description', required=False)


class MaintenanceGuidelineActivity(models.Model):
    _name = 'maintenance.guideline.activity'
    _description = 'Maintenance Guideline Activity'
    _check_company_auto = True

    sequence = fields.Integer(required=True, default=10)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    guideline_id = fields.Many2one('maintenance.guideline',
                                   string='Guideline',
                                   required=True,
                                   ondelete='cascade',
                                   index=True, copy=False,
                                   check_company=True)

    activity_id = fields.Many2one(comodel_name='guideline.activity',
                                  string='Activity', required=True)

    activity_att_documents = fields.Many2many(related='activity_id.att_documents')

    activity_code = fields.Char(related='activity_id.code', string='Code')
    activity_url_video = fields.Char(related='activity_id.url_video')

    def action_open_url_video(self):
        self.ensure_one()
        if self.activity_url_video:
            return {
                'type': 'ir.actions.act_url',
                'url': self.activity_url_video,
                'target': 'new',
            }
        else:
            raise Warning(_(f'the activity does not have an assigned video'))