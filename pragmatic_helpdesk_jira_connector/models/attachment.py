# -*- coding: utf-8 -*-
from odoo import api, fields, models, exceptions


class JiraIssueAttachment(models.Model):
    _inherit = 'ir.attachment'

    jira_id = fields.Char(string='Jira ID')
