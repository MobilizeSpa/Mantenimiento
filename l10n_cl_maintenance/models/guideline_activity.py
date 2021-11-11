from odoo import models, fields, api, _
from odoo.exceptions import Warning, ValidationError


class MaintenanceGuidelineActivity(models.Model):
    _name = 'guideline.activity'
    _description = 'Guideline Activity'
    _parent_name = "parent_id"
    _parent_store = True
    _rec_name = 'complete_name'
    _parent_order = "name"
    _check_company_auto = True

    sequence = fields.Integer(required=True, default=10)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    active = fields.Boolean('Active', default=True)

    code = fields.Char(string='Code', required=True, copy=False)
    name = fields.Char(string='Name', required=True, copy=False)

    display_name = fields.Char(compute="_compute_display_name")

    complete_name = fields.Char(
        'Complete Name', compute='_compute_complete_name',
        store=True)
    parent_id = fields.Many2one('guideline.activity',
                                'Parent Activity',
                                index=True,
                                ondelete='cascade',
                                check_company=True)

    parent_left = fields.Integer("Left Parent", index=1)
    parent_right = fields.Integer("Right Parent", index=1)
    child_count = fields.Integer(
        compute="_compute_child_count", string="Number of child equipments"
    )

    parent_path = fields.Char(index=True)
    parent_path_ids = fields.Char(compute='_compute_parent_path')
    child_ids = fields.One2many('guideline.activity', 'parent_id', 'Child Actities')

    @api.depends("child_ids")
    def _compute_child_count(self):
        for equipment in self:
            equipment.child_count = len(equipment.child_ids)

    def _compute_display_name(self):
        for equipment in self:
            equipment.display_name = equipment.complete_name

    @api.depends('name', 'parent_id.complete_name')
    def _compute_complete_name(self):
        for guideline in self:
            if guideline.parent_id:
                guideline.complete_name = '%s / %s' % (guideline.parent_id.complete_name, guideline.name)
            else:
                guideline.complete_name = guideline.name

    def preview_child_list(self):
        return {
            "name": "Child activity of %s" % self.name,
            "type": "ir.actions.act_window",
            "res_model": "guideline.activity",
            "res_id": self.id,
            "view_mode": "list,form",
            "context": {
                **self.env.context,
                "default_parent_id": self.id,
                "parent_id_editable": False,
            },
            "domain": [("id", "in", self.child_ids.ids)],
        }

    # @api.depends('parent_id')
    def _compute_parent_path(self):
        for guideline in self:
            if guideline.parent_id:
                x = '/%s/%s/' % (guideline.parent_id.parent_path_ids, guideline.id)
                x = x.replace('//', '/')
                guideline.parent_path_ids = x
            else:
                guideline.parent_path_ids = f'/{guideline.id}/'

    @api.constrains('parent_id')
    def _check_guideline_recursion(self):
        if not self._check_recursion():
            raise ValidationError(_('You cannot create recursive activities.'))
        return True

    @api.model
    def name_create(self, name):
        return self.create({'name': name}).name_get()[0]

    att_documents = fields.Many2many('ir.attachment', string='Documents', required=False)
    description = fields.Html(string='Description', required=False)

    url_ids = fields.One2many('activity.url', 'activity_id', 'Urls', copy=True, auto_join=True)
    url_video = fields.Char(string='Url video', compute='_compute_url_video')

    @api.depends('url_ids')
    def _compute_url_video(self):
        for rec in self:
            if rec.url_ids and len(rec.url_ids) > 0:
                rec.url_video = rec.url_ids[0].name
            else:
                rec.url_video = None

    def action_open_url_video(self):
        self.ensure_one()
        if self.url_video:
            return {
                'type': 'ir.actions.act_url',
                'url': self.url_video,
                'target': 'new',
            }
        else:
            raise Warning(_(f'the activity does not have an link assigned video'))

    @api.returns('self', lambda value: value.id)
    def copy(self, default=None):
        default = dict(default or {})

        try:
            default.setdefault('name', _("%s (copy)") % (self.name or ''))
            default.setdefault('code', _("%s (copy)") % (self.code or ''))
        except ValueError:
            default['code'] = _("%s (copy)") % (self.code or '')
            default['name'] = self.name
        return super(MaintenanceGuidelineActivity, self).copy(default)

    specialty_tag_ids = fields.Many2many(
        "hr.specialty.tag",
        "guideline_activity_tag_rel",
        "activity_id",
        "specialty_tag_id",
        string="Specialties",
        requerid=True
    )

    _sql_constraints = [
        ('unique_name', 'unique (name)', 'The activity name must be unique!'),
        ('unique_code', 'unique (code)', 'The activity code must be unique!'),
    ]


class ActivityUrl(models.Model):
    _name = 'activity.url'

    activity_id = fields.Many2one('guideline.activity', string='Activity', required=True, ondelete='cascade',
                                  index=True, copy=False)
    name = fields.Char(string='Name', required=True)
    description = fields.Char(string='Description', required=False)
