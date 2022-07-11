# -*- coding: utf-8 -*-
from odoo import api, fields, models, exceptions


class JiraProjectType(models.Model):
    _name = 'jira.project.type'
    _description = 'Jira Project Type'

    def jira_get_all(self):
        response = self.env['res.company'].search([], limit=1).get('project/type').json()
        for pt in response:
            self.jira_parse_response(pt)

    def jira_parse_response(self, response):
        project_type_dict = dict(
            key=response['key'],
            name=response['formattedKey'],
            description=response['descriptionI18nKey'],
        )
        project_type = self.env['jira.project.type'].search([('key', '=', response['key'])])
        if not project_type:
            project_type = self.env['jira.project.type'].create(project_type_dict)
        else:
            project_type.write(project_type_dict)
        return project_type

    def jira_key(self, key):
        project_type = self.search([('key', '=', key)])
        if not project_type:
            response = self.env['res.company'].search([], limit=1).get('project/type/' + key).json()
            project_type = self.jira_parse_response(response)
        return project_type

    name = fields.Char(required=1)
    key = fields.Char(required=1)
    description = fields.Char()
