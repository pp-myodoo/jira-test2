# -*- coding: utf-8 -*-
from odoo import api, fields, models, exceptions


class JiraProjectComponent(models.Model):
    _name = 'jira.project.component'
    _description = 'Jira Project Component'

    def send_to_jira(self):
        component_dict = dict(
            projectId=self.project_id.jira_id,
            name=self.name,
            project=self.project_id.key,
        )
        if not self.jira_id:
            response = self.env['res.company'].search([], limit=1).post('component', component_dict)
            self.jira_id = response.json()['id']
        else:
            response = self.env['res.company'].search([], limit=1).put('component/' + self.jira_id, component_dict)

    @api.model
    def create(self, vals):
        output = super(JiraProjectComponent, self).create(vals)
        if 'disable_mail_mail' not in self.env.context:
            if output.project_id and output.project_id.jira_id:
                output.send_to_jira()
        return output

    def write(self, vals):
        output = super(JiraProjectComponent, self).write(vals)
        if 'disable_mail_mail' not in self.env.context:
            if self.project_id and self.project_id.jira_id:
                self.send_to_jira()
        return output

    def unlink(self):
        jira_id = self.jira_id
        output = super(JiraProjectComponent, self).unlink()
        if jira_id:
            self.env['res.company'].search([], limit=1).delete('component/' + jira_id)
        return output

    def jira_get_all(self):
        for component in self.search([]):
            self.jira_parse_response(self.env['res.company'].search([], limit=1).get('component/' + component.jira_id).json())

    def jira_parse_response(self, response):
        component_dict = dict(
            jira_id=response['id'],
            name=response['name'],
            assignee_id=False,
            real_assignee_id=False,
            project_id=self.env['project.project'].jira_key(response['project']).id,
        )
        if 'assignee' in response:
            component_dict['assignee_id'] = self.env['res.users'].get_user_by_dict(response['assignee']).id
        if 'realAssignee' in response:
            component_dict['real_assignee_id'] = self.env['res.users'].get_user_by_dict(response['realAssignee']).id
        component = self.search([('jira_id', '=', component_dict['jira_id'])])
        if not component:
            component = self.create(component_dict)
        else:
            component.write(component_dict)
        return component

    def jira_key(self, id):
        component = self.search([('jira_id', '=', id)])
        if not component:
            component = self.jira_parse_response(self.env['res.company'].search([], limit=1).get('component/' + str(id)).json())
        return component

    def jira_dict(self, pc_dict):
        pc = self.search([('jira_id', '=', pc_dict['id'])])
        if not pc:
            pc = self.jira_parse_response(pc_dict)
        return pc

    project_id = fields.Many2one('project.project', ondelete='cascade')
    jira_id = fields.Char()
    name = fields.Char()
    assignee_id = fields.Many2one('res.users')
    real_assignee_id = fields.Many2one('res.users')
    issue_ids = fields.Many2many('project.task')
