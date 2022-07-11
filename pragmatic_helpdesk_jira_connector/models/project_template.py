# -*- coding: utf-8 -*-
from odoo import api, fields, models, exceptions


class JiraProjectTemplate(models.Model):
    _name = 'jira.project.template'
    _description = 'Jira Project Template'

    def jira_get_all(self):
        response = self.env['res.company'].search([], limit=1).get('templates', '/rest/project-templates/1.0/').json()
        for type in response['projectTemplatesGroupedByType']:
            for pt in type['projectTemplates']:
                self.jira_parse_response(pt)

    def jira_parse_response(self, response):
        project_template_dict = dict(
            name=response['name'],
            create_project=response['createProject'],
            description=response['description'],
            long_description=response['longDescriptionContent'],
            project_template_type_id=self.env['jira.project.type'].jira_key(response['projectTypeKey']).id,
            weight=response['weight'],
            key=response['itemModuleCompleteKey'],
        )
        project_template = self.search([('key', '=', response['itemModuleCompleteKey'])])
        if not project_template:
            project_template = self.create(project_template_dict)
        else:
            project_template.write(project_template_dict)
        return project_template

    def jira_key(self, key):
        pass

    name = fields.Char()
    key = fields.Char()
    create_project = fields.Boolean()
    description = fields.Char()
    long_description = fields.Char()
    project_template_type_id = fields.Many2one('jira.project.type')
    weight = fields.Integer()
