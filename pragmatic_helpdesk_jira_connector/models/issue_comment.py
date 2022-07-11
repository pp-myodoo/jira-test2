# -*- coding: utf-8 -*-
from odoo import api, fields, models, exceptions


class JiraIssueComment(models.Model):
    _inherit = 'mail.message'

    jira_id = fields.Char(string='Jira ID')
