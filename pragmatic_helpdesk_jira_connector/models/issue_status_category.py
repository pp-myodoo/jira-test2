# -*- coding: utf-8 -*-

from odoo import api, fields, models, exceptions


class JiraIssueStatusCategory(models.Model):
    _name = 'jira.issue.status.category'
    _description = 'Jira Issue Status Category'

    def jira_get_all(self):
        scategory = self.env['res.company'].search([], limit=1).get('statuscategory').json()
        for sc in scategory:
            self.jira_parse_response(sc)

    def jira_parse_response(self, response):
        sc_dict = dict(jira_id=response['id'], key=response['key'], name=response['name'])
        sc = self.search([('key', '=', sc_dict['key'])])
        if not sc:
            sc = self.create(sc_dict)
        else:
            sc.write(sc_dict)
        return sc

    def jira_key(self, key):
        sc = self.search([('key', '=', key)])
        if not sc:
            sc = self.jira_parse_response(self.env['res.company'].search([], limit=1).get('statuscategory/' + key).json())
        return sc

    jira_id = fields.Char(required=1)
    key = fields.Char(required=1)
    name = fields.Char(required=1)
