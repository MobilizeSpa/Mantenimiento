from odoo import models, fields, _
from odoo.exceptions import Warning


class MaintenanceGuidelineActivity(models.Model):
    _name = 'guideline.activity'
    _description = 'Guideline Activity'
    _check_company_auto = True

    sequence = fields.Integer(required=True, default=10)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)

    code = fields.Char(string='Code', required=True)
    name = fields.Char(string='Name', required=True)
    url_video = fields.Char(string='Url video', required=False)
    att_documents = fields.Many2many('ir.attachment', string='Documents', required=False)
    description = fields.Text(string='Description', required=False)

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
