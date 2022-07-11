# -*- coding: utf-8 -*-
from odoo import api, fields, models, exceptions


class JiraIssueResolution(models.Model):
    _name = 'jira.issue.resolution'
    _description = 'Jira Issue Resolution'

    def jira_get_all(self):
        resolutions = self.env['res.company'].search([], limit=1).get('resolution').json()
        for resolution in resolutions:
            self.jira_parse_response(resolution)

    def jira_parse_response(self, response):
        resolution_dict = dict(
            jira_id=response['id'],
            name=response['name'],
            description=response['description'],
        )
        resolution = self.search([('jira_id', '=', resolution_dict['jira_id'])])
        if not resolution:
            resolution = self.create(resolution_dict)
        else:
            resolution.write(resolution_dict)
        return resolution

    def jira_key(self, id):
        resolution = self.search([('jira_id', '=', id)])
        if not resolution:
            resolution = self.jira_parse_response(self.env['res.company'].search([], limit=1).get('resolution/' + id).json())
        return resolution

    jira_id = fields.Char(required=1)
    name = fields.Char(required=1)
    description = fields.Char(required=1)
