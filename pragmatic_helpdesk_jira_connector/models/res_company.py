# -*- coding: utf-8 -*-
from odoo import api, fields, models, exceptions, _
from datetime import datetime, date
import requests
from odoo.exceptions import Warning


class Jira_Config_Settings(models.Model):
    _inherit = 'res.company'
    _description = 'Jira Configuration'

    name = fields.Char(default='Jira Settings')
    url = fields.Char('Instance URL')
    jira_login = fields.Char()
    password = fields.Char(string='Jira Token')
    updated = fields.Date(default=date(2000, 1, 1))
    download_attachments = fields.Boolean(default=True)
    disable_sending_data = fields.Boolean(default=False)
    use_tempo_timesheets = fields.Boolean(default=False)
    cron_id = fields.Many2one('ir.cron')
    cron_active = fields.Boolean(related='cron_id.active')
    interval_number = fields.Integer(related='cron_id.interval_number')
    interval_type = fields.Selection(related='cron_id.interval_type')
    nextcall = fields.Datetime(related='cron_id.nextcall')

    def get(self, request, path='/rest/api/latest/', check=True):
        try:
            # self.log('GET ' + self.url + path + request)
            response = requests.get(self.url + path + request, auth=(self.jira_login, self.password), verify=False)
            if response.status_code != 200:
                return 404
            if check:
                self.check_response(response)
            return response

        except Exception as e:
            raise Warning("Oops Some error Occured" + str(e))

    def get_file(self, url):
        try:
            response = requests.get(url, auth=(self.jira_login, self.password), stream=True)
            self.check_response(response)
            return response
        except Exception as e:
            raise Warning("Oops Some error Occured" + str(e))

    def post(self, request, rdata=dict(), path='/rest/api/latest/'):
        try:
            if self.disable_sending_data:
                return False
            response = requests.post(self.url + path + request, auth=(self.jira_login, self.password), json=rdata)
            self.check_response(response)
            return response
        except Exception as e:
            raise Warning("Oops Some error Occured" + str(e))

    def post_file(self, request, filename, filepath):
        try:
            attachment = open(filepath, "rb")
            response = requests.post(self.url + '/rest/api/latest/' + request, auth=(self.jira_login, self.password),
                                     files={'file': (filename, attachment, 'application/octet-stream')},
                                     headers={'content-type': None, 'X-Atlassian-Token': 'nocheck'})
            self.check_response(response)
            return response
        except Exception as e:
            raise Warning("Oops Some error Occured" + str(e))

    def put(self, request, rdata=dict(), path='/rest/api/latest/'):
        try:
            if self.disable_sending_data:
                return False
            response = requests.put(self.url + path + request, auth=(self.jira_login, self.password), json=rdata)
            self.check_response(response)
            return response
        except Exception as e:
            raise Warning("Oops Some error Occured" + str(e))

    def delete(self, request, path='/rest/api/latest/'):
        try:
            if self.disable_sending_data:
                return False
            response = requests.delete(self.url + path + request, auth=(self.jira_login, self.password))
            self.check_response(response)
            return response
        except Exception as e:
            raise Warning("Oops Some error Occured" + str(e))

    def check_response(self, response):
        if response is False:
            return
        if response.status_code not in [200, 201, 204, 404]:
            try:
                resp_dict = response.json()
            except:
                raise exceptions.Warning('Response status code: ' + str(response.status_code))
            error_msg = ''
            try:
                if 'errorMessages' in resp_dict and resp_dict['errorMessages']:
                    for e in resp_dict['errorMessages']:
                        error_msg += e + '\n'
                if 'errors' in resp_dict and resp_dict['errors']:
                    for e in resp_dict['errors']:
                        error_msg += resp_dict['errors'][e] + '\n'
            except:
                raise exceptions.Warning(error_msg)

    def getall(self, request, path='/rest/api/latest/', searchobj='issues'):
        try:
            companies = self.env['res.company'].search([], limit=1).search([])
            startat = 0
            full_response = list()
            while True:
                response = self.get(request + '&startAt=' + str(startat), path).json()
                if 'errorMessages' in response:
                    return full_response
                startat += 50
                if type(response) is list:
                    full_response += response
                    responselen = len(response)
                else:
                    full_response.append(response[searchobj])
                    responselen = len(response[searchobj])
                if responselen < 50:
                    break
            return full_response
        except Exception as e:
            raise Warning("Oops Some error Occured" + str(e))

    def messageSend(self, response):
        message = ''
        if 'Message' in response:
            message = response['Message']
        view_id = self.env.ref('pragmatic_helpdesk_jira_connector.response_message_wizard_form').id
        if view_id:
            value = {
                'name': _('Message'),
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'response.message.wizard',
                'view_id': False,
                'context': {'message': message},
                'views': [(view_id, 'form')],
                'type': 'ir.actions.act_window',
                'target': 'new',
            }
            return value

    def test_connection(self):
        status_code = self.get('myself').status_code
        if status_code == 200:
            return self.messageSend({'Message': "Connection Check to Jira Successful !!"})
        else:
            return self.messageSend({'Message': "Connection Check to Jira Unsuccessful !!"})

    def update_jira(self):
        try:
            ctx = dict(self.env.context)
            ctx['disable_mail_mail'] = True
            ctx['disable_mail_message'] = True
            ctx['mail_create_nosubscribe'] = True
            self = self.with_context(ctx)
            models = ['res.users', 'jira.project.category', 'jira.project.component', 'jira.project.template',
                      'jira.project.type', 'project.project', 'jira.issue.priority', 'jira.issue.status.category',
                      'jira.status', 'jira.issue.link.type', 'project.task', 'jira.issue.resolution']
            if 'update' in self.env.context:
                models = [self.env.context['update']]
            for model in models:
                self.env[model].jira_get_all()
        except Exception as e:
            raise Warning("Oops Some error Occured" + str(e))

    def latest_jira_issue_update(self):
        try:
            ticket_ids = self.env['helpdesk.ticket'].search([('project_id', '!=', None)])
            for ticket_id in ticket_ids:
                ticket_id.update_jira()
        except Exception as e:
            raise Warning("Oops Some error Occured" + str(e))

    def latest_jira_project_update(self):
        self.env['project.project'].jira_get_all()

    def update_issue_status(self):
        self.env['helpdesk.ticket'].update_issue_status()

    def update_jira_issues(self):
        try:
            ctx = dict(self.env.context)
            ctx['disable_mail_mail'] = True
            ctx['disable_mail_message'] = True
            ctx['mail_create_nosubscribe'] = True
            self = self.with_context(ctx)
            models = ['project.task']
            if 'update' in self.env.context:
                models = [self.env.context['update']]
            for model in models:
                self.env[model].jira_get_all()
        except Exception as e:
            raise Warning("Oops Some error Occured" + str(e))

    @api.constrains('url')
    def constrains_url(self):
        try:
            if not self.url:
                return
            if not self.url.startswith('http://') and not self.url.startswith('https://'):
                raise exceptions.Warning('Url must start with http:// or https://')
            if self.url.endswith('/'):
                self.url = self.url[:-1]
        except Exception as e:
            raise Warning("Oops Some error Occured" + str(e))
