from odoo import models, fields, api, _


class MaintenanceRequestTask(models.Model):
    _name = 'maintenance.request.task'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Maintenance Request Task'
    _check_company_auto = True

    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    name = fields.Char(string='Name', required=True, copy=False, readonly=True, index=True,
                       default=lambda self: _('New'))

    activity_id = fields.Many2one('guideline.activity', 'Activity')

    employee_id = fields.Many2one('hr.employee', 'Employee', required=False, check_company=True)

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
        self.state = 'draft'

    def action_confirm(self):
        self.ensure_one()
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

    maintenance_guideline_id = fields.Many2one('maintenance.guideline', 'Guideline Of Maintenance',
                                               domain="[('equipment_id', '=', equipment_id)]", check_company=True
                                               )

    @api.onchange('maintenance_guideline_id')
    def onchange_maintenance_guideline_id(self):
        self.update(dict(maintenance_type=self.maintenance_guideline_id.maintenance_type))

    equipment_activity_id = fields.Many2one('maintenance.equipment.activity', 'Equipment Activity',
                                            related="maintenance_guideline_id.equipment_activity_id"
                                            )

    task_ids = fields.One2many('maintenance.request.task', 'request_id', string='Tasks',
                               required=False)

    task_done_percent = fields.Float(
        'Advance percentage', compute='_compute_task_done_percent',
        help='Percentage of completed tasks')

    @api.depends('task_ids')
    def _compute_task_done_percent(self):
        for rec in self:
            task_done_percent = 0
            if rec.task_ids:
                len_tasks = len(rec.task_ids)
                len_done = rec.task_ids.search_count([('state', '=', 'done')])
                value = (len_done / len_tasks) * 100
                task_done_percent = value
            rec.task_done_percent = task_done_percent

    task_done_count = fields.Integer(
        'Advance', compute='_compute_task_done_count',
        help='Number of completed tasks')

    @api.depends('task_ids')
    def _compute_task_done_count(self):
        for rec in self:
            task_done_count = 0
            if rec.task_ids:
                task_done_count = rec.task_ids.search_count([('state', '=', 'done')])
            rec.task_done_count = task_done_count
    # task_state = fields.Selection([
    #     ('todo', 'To do'),
    #     ('process', 'Process'),
    #     ('done', 'Done')], string='Task State',
    #     compute='_compute_task_state',
    #     help='Status based on tasks\nTo do: All tasks to be done\n'
    #          'process: Some tasks in progress\ndone: all tasks finished.')
    #
    # @api.depends('task_ids')
    # def _compute_task_state(self):
    #     for rec in self:
    #         len_task = len(self.task_ids)
    #         len_draft = rec.task_ids.search_count([('state', '=', 'draft')])
    #         len_done = len_task - len_draft
    #         if len_task == len_draft:
    #             rec.task_state = 'todo'
    #         elif len_task == len_done:
    #             rec.task_state = 'done'
    #         else:
    #             rec.task_state = 'process'

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

    def write(self, values):

        # Add code here
        if 'maintenance_guideline_id' in values:
            maintenance_guideline_id = self.maintenance_guideline_id.browse(int(values.get('maintenance_guideline_id')))
            common_activities = maintenance_guideline_id.activities_ids
            data_task = []
            for activity in common_activities:
                data_task.append((0, 0, dict(activity_id=activity.activity_id.id,
                                             request_id=self.id)))
            values.update(dict(task_ids=data_task))
            if self.task_ids:
                # for task in self.task_ids:
                #     # if not task.activity_id in maintenance_guideline_id.activities_ids.mapped('activity_id'):
                #     task.unlink()
                self.task_ids = [(6, 0, [])]

        return super(MaintenanceRequest, self).write(values)

    @api.model
    def create(self, values):
        # Add code here
        res = super(MaintenanceRequest, self).create(values)
        if 'maintenance_guideline_id' in values:
            maintenance_guideline_id = self.maintenance_guideline_id.browse(int(values.get('maintenance_guideline_id')))
            common_activities = maintenance_guideline_id.activities_ids
            data_task = []
            for activity in common_activities:
                data_task.append((0, 0, dict(activity_id=activity.activity_id.id,
                                             request_id=res.id)))
            res.write(dict(task_ids=data_task))
        return res
