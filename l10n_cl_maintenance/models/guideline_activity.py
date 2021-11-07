from odoo import models, fields, api, _
from odoo.exceptions import Warning, ValidationError


class MaintenanceGuidelineActivity(models.Model):
    _name = 'guideline.activity'
    _description = 'Guideline Activity'
    _parent_name = "parent_id"
    _parent_store = True
    _rec_name = 'complete_name'
    _order = 'complete_name'
    _check_company_auto = True

    sequence = fields.Integer(required=True, default=10)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)

    code = fields.Char(string='Code', required=True, copy=False)
    name = fields.Char(string='Name', required=True, copy=False)

    complete_name = fields.Char(
        'Complete Name', compute='_compute_complete_name',
        store=True)
    parent_id = fields.Many2one('guideline.activity', 'Parent Activity',
                                index=True, ondelete='cascade', check_company=True)
    parent_path = fields.Char(index=True)
    child_ids = fields.One2many('guideline.activity', 'parent_id', 'Child Actities')

    @api.depends('name', 'parent_id.complete_name')
    def _compute_complete_name(self):
        for category in self:
            if category.parent_id:
                category.complete_name = '%s / %s' % (category.parent_id.complete_name, category.name)
            else:
                category.complete_name = category.name

    @api.constrains('parent_id')
    def _check_category_recursion(self):
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
            raise Warning(_(f'the activity does not have an assigned video'))

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
