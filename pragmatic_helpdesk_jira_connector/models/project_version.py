# -*- coding: utf-8 -*-
from odoo import api, fields, models, exceptions
from dateutil import parser


class JiraProjectVersion(models.Model):
    _name = 'jira.project.version'
    _description = 'Jira Project Version'

    def send_to_jira(self):
        version_dict = dict(
            projectId=self.project_id.jira_id,
            name=self.name,
            project=self.project_id.key,
        )
        if not self.jira_id:
            response = self.env['res.company'].search([], limit=1).post('version', version_dict)
            self.jira_id = response.json()['id']
        else:
            response = self.env['res.company'].search([], limit=1).put('version/' + self.jira_id, version_dict)

    @api.model
    def create(self, vals):
        output = super(JiraProjectVersion, self).create(vals)
        if 'disable_mail_mail' not in self.env.context:
            if output.project_id and output.project_id.jira_id:
                output.send_to_jira()
        return output

    def write(self, vals):
        output = super(JiraProjectVersion, self).write(vals)
        if 'disable_mail_mail' not in self.env.context:
            if self.project_id and self.project_id.jira_id:
                self.send_to_jira()
        return output

    def unlink(self):
        jira_id = self.jira_id
        output = super(JiraProjectVersion, self).unlink()
        if jira_id:
            self.env['res.company'].search([], limit=1).delete('version/' + jira_id)
        return output

    def jira_get_all(self):
        for version in self.search([]):
            self.jira_parse_response(self.env.ref('jira.connector_jira_settings_record').get('version/' + version.jira_id).json())

    def jira_parse_response(self, response):
        version_dict = dict(
            jira_id=response['id'],
            name=response['name'],
            archived=response['archived'],
            released=response['released'],
            project_id=self.env['project.project'].get_jira_id(response['projectId']).id,
            description=False,
            overdue=False,
            release_date=False,
        )
        if 'description' in response:
            version_dict['description'] = response['description']
        if 'overdue' in response:
            version_dict['overdue'] = response['overdue']
        if 'releaseDate' in response:
            version_dict['release_date'] = parser.parse(response['releaseDate']).date()
        version = self.search([('jira_id', '=', response['id'])])
        if not version:
            version = self.create(version_dict)
        else:
            version.write(version_dict)
        return version

    def jira_key(self, id):
        version = self.search([('jira_id', '=', id)])
        if not version:
            version = self.jira_parse_response(self.env['res.company'].search([], limit=1).get('version/' + id).json())
        return version

    def jira_dict(self, version_dict):
        version = self.search([('jira_id', '=', version_dict['id'])])
        if not version:
            version = self.jira_parse_response(version_dict)
        return version

    name = fields.Char()
    description = fields.Char()
    jira_id = fields.Char()
    archived = fields.Boolean()
    released = fields.Boolean()
    release_date = fields.Date()
    overdue = fields.Boolean()
    project_id = fields.Many2one('project.project', ondelete='cascade')
