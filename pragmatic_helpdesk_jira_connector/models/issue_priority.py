# -*- coding: utf-8 -*-
from odoo import api, fields, models, exceptions


class JiraIssuePriority(models.Model):
    _name = 'jira.issue.priority'
    _description = 'Jira Issue Priority'

    def jira_get_all(self):
        priority = self.env['res.company'].search([], limit=1).get('priority').json()
        for p in priority:
            self.jira_parse_response(p)

    def jira_parse_response(self, response):
        priority_dict = dict(
            jira_id=response['id'],
            name=response['name'],
            description=response['description'],
        )
        priority = self.search([('jira_id', '=', priority_dict['jira_id'])])
        if not priority:
            priority = self.create(priority_dict)
        else:
            priority.write(priority_dict)
        return priority

    def jira_key(self, id):
        priority = self.search([('jira_id', '=', id)])
        if not priority:
            priority = self.jira_parse_response(
                self.env['res.company'].search([], limit=1).get('priority/' + id).json()
            )
        return priority

    jira_id = fields.Char(required=1)
    name = fields.Char(required=1)
    description = fields.Char(required=1)
