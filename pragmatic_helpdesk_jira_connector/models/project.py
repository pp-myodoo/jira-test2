# -*- coding: utf-8 -*-

from odoo import api, fields, models, exceptions


class JiraProject(models.Model):
    _inherit = 'project.project'

    @api.onchange('jira_project')
    def onchange_context(self):
        if self.jira_project:
            if self.user_id and not self.user_id.jira_id:
                self.user_id = False
            return {'domain': {'user_id': [('jira_id', '!=', False)]}}
        else:
            return {'domain': {'user_id': []}}

    def jira_get_all(self):
        response = self.env['res.company'].search([], limit=1).get('project').json()
        for p in response:
            self.jira_parse_response(self.env['res.company'].search([], limit=1).get('project/' + p['key']).json())

    def jira_parse_response(self, response):
        if response == 404:
            return True
        project_dict = dict(
            jira_id=response['id'],
            key=response['key'],
            description=False,
            user_id=self.env['res.users'].get_user_by_dict(response['lead']).id,
            name=response['name'],
            project_type_id=self.env['jira.project.type'].jira_key(response['projectTypeKey']).id,
            category_id=False,
            url=False,
            type_ids=[(6, 0, [])],
        )

        if 'projectCategory' in response:
            project_dict['category_id'] = self.env['jira.project.category'].jira_key(response['projectCategory']['id']).id
        if 'url' in response:
            project_dict['url'] = response['url']
        if response['description']:
            project_dict['description'] = response['description']

        issue_type_ids = list()
        for issue_type in response['issueTypes']:
            issue_type_ids.append(self.env['jira.issue.type'].jira_dict(issue_type).id)
        project_dict['issue_type_ids'] = [(6, 0, issue_type_ids)]
        project = self.search([('key', '=', project_dict['key'])])

        if not project:
            project = self.create(project_dict)
        else:
            project.write(project_dict)

        return project

    def jira_key(self, key):
        project = self.search([('key', '=', key)])
        if not project:
            project = self.jira_parse_response(self.env['res.company'].search([], limit=1).get('project/' + key).json())
        return project

    def get_jira_id(self, id):
        project = self.search([('jira_id', '=', id)])
        if not project:
            project = self.jira_parse_response(self.env['res.company'].search([], limit=1).get('project/' + id).json())
        return project

    @api.depends('key')
    def name_get(self):
        result = []
        for project in self:
            if project.key:
                result.append((project.id, '[' + project.key + '] ' + project.name))
            else:
                result.append((project.id, project.name))
        return result

    jira_id = fields.Char()
    key = fields.Char()
    description = fields.Text()
    url = fields.Char()
    user_id = fields.Many2one(default=False)
    project_type_id = fields.Many2one('jira.project.type')
    project_template_id = fields.Many2one('jira.project.template')
    category_id = fields.Many2one('jira.project.category')
    component_ids = fields.One2many('jira.project.component', 'project_id', string='Components')
    issue_type_ids = fields.Many2many('jira.issue.type', string='Issue Types')
    version_ids = fields.One2many('jira.project.version', 'project_id', string='Versions')
    jira_project = fields.Boolean(default=True)
