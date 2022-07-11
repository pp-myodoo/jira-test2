# -*- coding: utf-8 -*-
from odoo import api, fields, models, exceptions
import random


class JiraUser(models.Model):
    _inherit = 'res.users'

    def action_reset_password(self):
        if 'disable_mail_mail' in self.env.context:
            return
        super(JiraUser, self).action_reset_password()

    def jira_get_all(self):
        response = self.env['res.company'].search([], limit=1).getall('user/search?query="."&includeInactive=true')
        for r in response:
            self.jira_parse_response(r)

    def jira_parse_response(self, response):
        if 'errorMessages' in response:
            key = response['errorMessages'][0][len('The user with the key \''):-len('\' does not exist')]
            user_dict = dict(
                jira_accountId=key,
                short_name=key,
                login=key,
                name=key,
                jira_active=False,
            )
        else:
            login = ''
            final_user_name = ''
            rand = random.randint(11, 99999)
            first_name = list(response['displayName'].split())
            if first_name[0] and first_name[-1]:
                final_user_name = first_name[0] + "_" + first_name[-1] + "_" + str(rand)
            else:
                final_user_name = first_name[0]
            if 'emailAddress' not in response:
                login = final_user_name
            else:
                login = final_user_name

            user_dict = dict(
                jira_accountId=response['accountId'],
                login=login,
                name=response['displayName'],
                jira_active=response['active'],
            )
        user = self.env['res.users'].search([('jira_accountId', '=', user_dict['jira_accountId'])])
        if not user:
            if response and response.get("displayName"):
                user_ids = self.env['res.users'].search([('name', '=', response.get("displayName"))])
                if user_ids and user_ids.jira_active == False:
                    user_ids.write({'jira_accountId': response['accountId']})
                else:
                    user = self.env['res.users'].sudo().create(user_dict)
                    self.env['hr.employee'].sudo().create(dict(user_id=user.id))
        else:
            pass
        return user

    def jira_key(self, account_id):
        user = self.search([('jira_accountId', '=', account_id)])
        if not user:
            user = self.jira_parse_response(self.env['res.company'].search([], limit=1).get('user?accountId=' + account_id, check=False).json())
        return user

    def get_user_by_dict(self, user_dict):
        if 'key' in user_dict:
            return self.jira_key(user_dict['key'])
        else:
            return self.jira_key(user_dict['accountId'])

    jira_accountId = fields.Char()
    short_name = fields.Char()
    name = fields.Char(required=1)
    jira_active = fields.Boolean(default=False)
