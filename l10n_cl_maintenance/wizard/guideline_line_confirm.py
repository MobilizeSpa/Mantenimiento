from odoo import fields, models, api


class GuidelineLineConfirm(models.TransientModel):
    _name = 'guideline.line.confirm'
    _description = 'Delete line guideline confirm'

    line_guideline = fields.Many2one(comodel_name='maintenance.guideline.activity',
                                     string='Guideline line',
                                     required=True)

    text_message = fields.Char(string='Text message', required=False)

    lines_dependent = fields.Many2many(
        comodel_name='maintenance.guideline.activity',
        string='Lines_dependent')

    @api.onchange('line_guideline')
    def _onchange_line_guideline(self):
        lines = self._get_lines_dependent()
        data = [(6, 0, [])]
        if lines:
            data = [(6, 0, lines.ids)]
        self.lines_dependent = data

    def _get_lines_dependent(self):
        lines_dependent = self.line_guideline.guideline_id.activities_ids
        my_id = f'/{self.line_guideline.activity_id.id}/'
        to_delete = lines_dependent.filtered(
            lambda i: my_id in i.activity_id.parent_path_ids and i.id != self.line_guideline.id)
        return to_delete

    def btn_confirm(self):
        lines_dependent = self.line_guideline.guideline_id.activities_ids
        my_id = f'/{self.line_guideline.activity_id.id}/'
        to_delete = lines_dependent.filtered(lambda i: my_id in i.activity_id.parent_path_ids)
        to_delete.unlink()
