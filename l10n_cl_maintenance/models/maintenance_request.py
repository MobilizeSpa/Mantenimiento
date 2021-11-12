from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class MaintenanceRequestTask(models.Model):
    _name = 'maintenance.request.task'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Maintenance Request Task'
    _check_company_auto = True

    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    name = fields.Char(string='Name', required=True, copy=False, readonly=True, index=True,
                       default=lambda self: _('New'))

    activity_id = fields.Many2one('guideline.activity', 'Activity')
    activity_speciality_ids = fields.Many2many(related='activity_id.specialty_tag_ids')

    employee_id = fields.Many2one('hr.employee', 'Employee', required=False, check_company=True)
    #
    # flag_domain_employee = fields.Boolean(compute='_compute_flag_domain_employee')
    #
    # @api.depends('activity_speciality_ids')
    # def _compute_flag_domain_employee(self):
    #     for rec in self:
    #         pass

    request_id = fields.Many2one(
        comodel_name='maintenance.request',
        string='Request', ondelete='cascade',
        required=True)

    state = fields.Selection(
        string='State',
        selection=[('draft', 'To do'),
                   ('done', 'Done'), ],
        required=True, default='draft')

    def action_draft(self):
        self.ensure_one()
        tasks_request = self.search([('request_id', '=', self.request_id.id)])
        for task in tasks_request:
            if self.activity_id.name in task.activity_id.complete_name:
                task.state = 'draft'

    def action_confirm(self):
        self.ensure_one()
        if self.activity_id.parent_id:
            task_dependent = self.search(
                [('activity_id', '=', self.activity_id.parent_id.id), ('request_id', '=', self.request_id.id)])
            if task_dependent and task_dependent.state == 'done':
                self.state = 'done'
            else:
                raise ValidationError(_(f'Task {task_dependent.name} pending validation'))
        else:
            self.state = 'done'

    @api.model
    def create(self, values):
        # Add code here
        if values.get('name', _('New')) == _('New'):
            name_seq = self.env['ir.sequence'].next_by_code('mtn.request.sequence')
            values.update(dict(name=name_seq))
        return super(MaintenanceRequestTask, self).create(values)


class MaintenanceRequest(models.Model):
    _inherit = 'maintenance.request'

    maintenance_guideline_ids = fields.Many2many(comodel_name='maintenance.guideline',
                                                 string='Guidelines Of Maintenance',
                                                 domain="[('equipment_id', '=', equipment_id)]",
                                                 check_company=True)

    # @api.onchange('maintenance_guideline_id')
    # def onchange_maintenance_guideline_id(self):
    #     self.update(dict(maintenance_type=self.maintenance_guideline_id.maintenance_type))

    # equipment_activity_id = fields.Many2one('maintenance.equipment.activity',
    #                                         'Equipment Activity',
    #                                         related="maintenance_guideline_id.equipment_activity_id")

    task_ids = fields.One2many('maintenance.request.task',
                               'request_id', string='Tasks', required=False)

    task_done_percent = fields.Float('Advance percentage', compute='_compute_task_done_percent',
                                     help='Percentage of completed tasks')

    task_done_count = fields.Integer('Advance', compute='_compute_task_done_count',
                                     help='Number of completed tasks')

    @api.depends('task_ids', 'task_done_count')
    def _compute_task_done_percent(self):
        for rec in self:
            task_done_percent = 0
            if rec.task_ids:
                cant_tasks = len(rec.task_ids)
                value = (rec.task_done_count / cant_tasks) * 100
                task_done_percent = value
            rec.task_done_percent = task_done_percent

    @api.depends('task_ids')
    def _compute_task_done_count(self):
        for rec in self:
            task_done_count = 0
            if rec.task_ids:
                tasks_done = rec.task_ids.filtered(lambda l: l.state == 'done')
                # task_done_count = rec.task_ids.search_count([('state', '=', 'done')])
                if tasks_done:
                    task_done_count = len(tasks_done)

            rec.task_done_count = task_done_count

    task_count = fields.Integer('Quantity activities', compute='compute_count_tasks')

    def compute_count_tasks(self):
        for record in self:
            record.task_count = len(record.task_ids)

    def get_tasks(self):
        self.ensure_one()
        action = self.env.ref('l10n_cl_maintenance.maintenance_request_task_action').read()[0]
        action['domain'] = [('request_id', '=', self.id)]
        action['context'] = dict(self._context, create=False)
        if self.task_ids:
            if len(self.task_ids) == 1:
                temp_id = self.task_ids[:1]
                res = self.env.ref('l10n_cl_maintenance.maintenance_request_task_view_form', False)
                form_view = [(res and res.id or False, 'form')]
                action['views'] = form_view
                action['res_id'] = temp_id.id
        else:
            action['views'] = action['views'][1:]
        return action

    guideline_speciality_ids = fields.Many2many(
        comodel_name='hr.specialty.tag',
        compute='_compute_guideline_speciality_ids',
        string='Specialities')

    @api.depends('maintenance_guideline_ids')
    def _compute_guideline_speciality_ids(self):
        for rec in self:
            set_speciality = set()
            for guideline in rec.maintenance_guideline_ids:
                for line in guideline.activities_ids:
                    for speciality in line.activity_speciality_ids:
                        set_speciality.add(speciality.id)
            rec.guideline_speciality_ids = [(6, 0, list(set_speciality))]

    def write(self, values):
        # Add code here
        if 'maintenance_guideline_ids' in values:
            aux_ids = values.get('maintenance_guideline_ids')
            ids = []
            for aux in aux_ids:
                ids += aux[2]
            maintenance_guideline_ids = self.env['maintenance.guideline'].browse(ids)
            data_task = []
            for guideline in maintenance_guideline_ids:
                guideline.bool_in_request = True
                common_activities = guideline.activities_ids
                for line in common_activities:
                    data_task.append((0, 0, dict(activity_id=line.activity_id.id,
                                                 request_id=self.id)))
            values.update(dict(task_ids=data_task))
            if self.task_ids:
                self.task_ids = [(6, 0, [])]

        return super(MaintenanceRequest, self).write(values)

    @api.model
    def create(self, values):
        # Add code here
        res = super(MaintenanceRequest, self).create(values)
        if 'maintenance_guideline_ids' in values:
            aux_ids = values.get('maintenance_guideline_ids')
            ids = []
            for aux in aux_ids:
                ids += aux[2]
            maintenance_guideline_ids = self.env['maintenance.guideline'].browse(ids)
            data_task = []
            for guideline in maintenance_guideline_ids:
                guideline.bool_in_request = True
                common_activities = guideline.activities_ids
                for line in common_activities:
                    data_task.append((0, 0, dict(activity_id=line.activity_id.id,
                                                 request_id=res.id)))
            res.write(dict(task_ids=data_task))
        return res
