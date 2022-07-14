import logging

from odoo import fields, api, models, exceptions, _
from odoo.exceptions import Warning, UserError
from dateutil import parser
import json
import html2text
from odoo.addons.helpdesk.models.helpdesk_ticket import HelpdeskTicket
import logging

_logger = logging.getLogger(__name__)


class HelpdeskTicketInherit(models.Model):
    _inherit = 'helpdesk.ticket'

    @api.depends('issue_type', 'issue_type.name')
    def compute_is_epic(self):
        for iss_id in self:
            if iss_id.issue_type and iss_id.issue_type.name == 'Epic':
                iss_id.is_epic = True
            elif iss_id.issue_type and iss_id.issue_type.name == 'Sub-task':
                iss_id.is_subtask = True

            elif iss_id.issue_type and iss_id.issue_type.name in ['Bug', 'Story', 'Task']:
                iss_id.is_subtask = False

    @api.model
    def default_get(self, fields):
        jira_isssue_types = ''
        vals = super(HelpdeskTicketInherit, self).default_get(fields)
        jira_isssue_types = self.env['jira.issue.type'].search([('name', '=', 'Bug')], limit=1)
        if jira_isssue_types:
            vals.update({'issue_type': jira_isssue_types.id})
        return vals

    reporter_id = fields.Many2one('res.users', string='Reporter', domain="[('jira_accountId', '!=', None)]")
    project_id = fields.Many2one('project.project', 'Project', domain="[('jira_id', '!=', None)]")
    issue_type = fields.Many2one('jira.issue.type', 'Issue Type')
    key = fields.Char()
    jira_id = fields.Char()
    priority_id = fields.Many2one('jira.issue.priority', 'Jira Priority')
    link_ids = fields.One2many('jira.issue.link.single', 'task_id')
    jira_status = fields.Many2one('jira.status', string='Status', domain="[('jira_id', '!=', None)]")
    parent_id = fields.Many2one('helpdesk.ticket', string='Parent Task', index=True)
    is_subtask = fields.Boolean(compute=compute_is_epic, store=True)
    is_epic = fields.Boolean(compute=compute_is_epic, store=True)
    show_jira_details = fields.Boolean('Use Ticket For Jira ')
    # ============================= ADDED PART =============================
    tag_ids = fields.Many2many('helpdesk.tag', string='Tags', required=True)  # added required param
    jira_tag_ids = fields.Many2many('helpdesk.tag', 'helpdesk_jira_tag_helpdesk_ticket_rel', 'jira_tag_id',
                                    'ticket_id', string='Jira Tags')  # added new relation

    # ============================= ADDED PART =============================

    @api.onchange('project_id')
    def onchange_project_id(self):
        if self.project_id.issue_type_ids:
            return {'domain': {'issue_type': [('id', 'in', self.project_id.issue_type_ids.ids)]}}

        else:
            return {'domain': {'issue_type': []}}

    def create_jira_dict(self, type):
        jira_dict = dict(
            fields=dict()
        )
        if self.project_id and type == 'CREATE':
            jira_dict['fields']['project'] = dict(id=self.env['project.project'].browse(self.project_id.id).jira_id)
        if self.name:
            jira_dict['fields']['summary'] = self.name
        if self.issue_type:
            jira_dict['fields']['issuetype'] = dict(id=self.env['jira.issue.type'].browse(self.issue_type.id).jira_id)
        if self.description:
            jira_dict['fields']['description'] = html2text.html2text(self.description)
        if self.user_id:
            user_jira_id = self.env['res.users'].browse(self.user_id.id).jira_accountId
            if user_jira_id:
                jira_dict['fields']['assignee'] = dict(id=user_jira_id)
            else:
                raise Warning(_('The assignee specified is not a  Jira user.'))
        if self.reporter_id:
            repo_jira_id = self.env['res.users'].browse(self.reporter_id.id).jira_accountId
            if repo_jira_id:
                jira_dict['fields']['reporter'] = dict(id=repo_jira_id)
            else:
                raise Warning(_('The reporter specified is not a  Jira user.'))
        if self.priority_id:
            jira_dict['fields']['priority'] = dict(
                id=self.env['jira.issue.priority'].browse(self.priority_id.id).jira_id)
        if self.parent_id:
            jira_dict['fields']['parent'] = dict(key=self.env['helpdesk.ticket'].browse(self.parent_id.id).key)

        if self.jira_status and type == 'WRITE':
            stage_obj = self.env['jira.status'].browse(self.jira_status.id)
            if not stage_obj.jira_id:
                raise exceptions.ValidationError('Selected stage must be connected to jira')
            response = self.env['res.company'].search([], limit=1).get('issue/' + self.key + '/transitions').json()
            allowed_transitions = dict()
            for t in response['transitions']:
                allowed_transitions[int(t['to']['id'])] = int(t['id'])
            if int(stage_obj.jira_id) not in allowed_transitions:
                raise exceptions.ValidationError('Unallowed transition')
            response = self.env['res.company'].search([], limit=1).post('issue/' + self.key + '/transitions',
                                                                        dict(transition=dict(id=allowed_transitions[
                                                                            int(stage_obj.jira_id)])))
        return jira_dict

    def update_issue_status(self):
        response = self.env['res.company'].search([], limit=1).getall(
            'search?includeInactive=True&fields=*all&validateQuery=strict&jql=updatedDate >= "-1d" ORDER BY updatedDate asc')
        for resp in response:
            for r in resp:
                self.jira_parse_response(r, True)
                self.env.cr.commit()

    def jira_parse_response(self, response, update=False):
        if response == 404:
            return 404
        if response != 404:
            issue_dict = dict(
                jira_id=response['id'],
                key=response['key'],
                name=response['fields']['summary'],
                issue_type=self.env['jira.issue.type'].jira_dict(response['fields']['issuetype']).id,
                project_id=self.env['project.project'].jira_key(response['fields']['project']['key']).id,
                priority_id=False,
                jira_status=self.env['jira.status'].jira_dict(response['fields']['status']).id,
                description=False,
                user_id=self.env['res.users'].get_user_by_dict(response['fields']['creator']).id,
                reporter_id=self.env['res.users'].get_user_by_dict(response['fields']['reporter']).id,
                parent_id=False,
            )
            if response['fields']['description']:
                issue_dict['description'] = response['fields']['description']
            if 'assignee' in response['fields'] and response['fields']['assignee']:
                issue_dict['user_id'] = self.env['res.users'].get_user_by_dict(response['fields']['assignee']).id
            if 'priority' in response['fields'] and response['fields']['priority']:
                issue_dict['priority_id'] = self.env['jira.issue.priority'].jira_key(
                    response['fields']['priority']['id']).id
            # if 'parent' in response['fields'] and response['fields']['parent']:
            #     issue_dict['parent_id'] = self.jira_key(response['fields']['parent']['key']).id

            # ============================= ADDED PART =============================
            # GETTING COMMENTS AND LABELS FROM JIRA
            ticket = self.env['helpdesk.ticket'].search([('jira_id', '=', response['id'])])
            ticket_id = ticket.id

            if response['fields']['comment']:
                comments_dict = response['fields']['comment']['comments']
                for comment in comments_dict:

                    comment_obj = self.env['mail.message'].search([('jira_id', '=', comment['id'])])
                    comment_id = comment_obj.id
                    user = self.env['res.users'].search([('jira_accountId', '=', comment['author']['accountId'])])
                    author_id = user.partner_id.id

                    if ticket_id and author_id and not comment_id:
                        self.env['mail.message'].create({
                            'res_id': ticket_id,
                            'jira_id': comment['id'],
                            'model': 'helpdesk.ticket',
                            'message_type': 'comment',
                            'body': comment['body'],
                            'author_id': author_id
                        })
                    elif ticket_id and author_id and comment_id:
                        comment_obj.write({
                            'body': comment['body']
                        })

            if response['fields']['labels']:
                labels_dict = response['fields']['labels']

                if ticket_id:

                    # remove deleted tags from sync list and ticket tags list
                    for tag in ticket.jira_tag_ids:
                        tag_removed = True
                        for label in labels_dict:
                            if tag.name == label:
                                tag_removed = False
                        if tag_removed:
                            _logger.info(f"UNLINK: {tag.name}")
                            ticket.tag_ids = [(3, tag.id)]  # unlink
                            ticket.jira_tag_ids = [(3, tag.id)]  # unlink

                    # add new tags to sync list
                    for label in labels_dict:
                        helpdesk_tag = self.env['helpdesk.tag'].search([('name', '=', label)])
                        if not helpdesk_tag:
                            helpdesk_tag = self.env['helpdesk.tag'].create({
                                'name': label
                            })
                        ticket.jira_tag_ids = [(4, helpdesk_tag.id)]  # link

                    # link new sync list to ticket tags list
                    for tag in ticket.jira_tag_ids:
                        ticket.tag_ids = [(4, tag.id)]  # link

            # ============================= ADDED PART =============================

            issue = self.search([('key', '=', issue_dict['key'])])
            if issue:
                issue.write(issue_dict)

            return issue

    def jira_key(self, key):
        project = self.search([('key', '=', key)])
        if not project:
            project = self.jira_parse_response(
                self.env['res.company'].search([], limit=1).get('project/' + key)
            )
        return project

    def update_jira(self):
        try:
            response = None
            for help_tict_id in self:
                if help_tict_id.project_id.jira_project and not help_tict_id.jira_id:
                    issue_dict = help_tict_id.create_jira_dict('CREATE')
                    response = self.env['res.company'].search([], limit=1).post('issue', issue_dict)
                    # help_tict_id.id = response.json()['id']
                    # help_tict_id.key = response.json()['key']
                    help_tict_id.write(dict(
                        jira_id=response.json()['id'],
                        key=response.json()['key']
                    ))
                    if help_tict_id.jira_status:
                        help_tict_id.write(dict(jira_status=help_tict_id.jira_status.id))

                if help_tict_id.project_id.jira_project and help_tict_id.jira_id:
                    issue_dict = help_tict_id.create_jira_dict('WRITE')
                    if issue_dict['fields']:
                        response = self.env['res.company'].search([], limit=1).put('issue/' + help_tict_id.jira_id,
                                                                                   issue_dict)

                if help_tict_id.jira_id:
                    attachment_ids = self.env['ir.attachment'].search(
                        [('res_id', '=', help_tict_id.id), ('res_model', '=', 'helpdesk.ticket')])

                    for attachment_id in attachment_ids:
                        if attachment_id and not attachment_id.jira_id:
                            filepath = self.env['ir.attachment']._filestore() + '/' + attachment_id.store_fname
                            response = self.env['res.company'].search([], limit=1).post_file(
                                'issue/' + help_tict_id.jira_id + '/attachments',
                                filename=attachment_id.name, filepath=filepath)
                            attachment_id.jira_id = response.json()[0]['id']

                if help_tict_id.key:
                    comment_ids = self.env['mail.message'].search(
                        [('res_id', '=', help_tict_id.id), ('model', '=', 'helpdesk.ticket'),
                         ('message_type', '=', 'comment')])

                    if comment_ids:
                        for comment_id in comment_ids:
                            if comment_id.body:
                                data = {"body": comment_id.body[3:-4]}
                                _logger.info(f"COMMENT DATA: {data}")
                            if (data and help_tict_id.key) and not comment_id.jira_id:
                                response = self.env['res.company'].search([], limit=1).post(
                                    'issue/' + help_tict_id.key + '/comment', data, )
                                comment_id.jira_id = response.json()['id']

                    # ============================= ADDED PART =============================
                    # SENDING COMMENT AUTHOR ID

                            if comment_id.author_id:
                                user = self.env['res.users'].search(['partner_id', '=', comment_id.author_id.id])
                                if user.jira_accountId:
                                    _logger.info(f"USER JIRA ACCOUNT ID: {user.jira_accountId}")
                                    user_data = {"author": {"accountId": str(user.jira_accountId)}}
                                    _logger.info(f"COMMENT USER DATA: {user_data}")
                                if (user_data and help_tict_id.key) and not comment_id.jira_id:
                                    response = self.env['res.company'].search([], limit=1).post(
                                        'issue/' + help_tict_id.key + '/comment', user_data, )

                    # SENDING LABELS TO JIRA
                    if help_tict_id.tag_ids:

                        # remove old tags from jira
                        tags_remove_dict = {'update': {'labels': ''}}
                        tags_remove_list = []

                        for jira_tag in help_tict_id.jira_tag_ids:
                            tag_dict = dict()
                            tag_dict['remove'] = jira_tag.name
                            tags_remove_list.append(tag_dict)

                        tags_remove_dict['update']['labels'] = tags_remove_list

                        _logger.info(f'TAGS LIST: {tags_remove_list}')
                        _logger.info(f'TAGS REMOVE DICT: {tags_remove_dict}')

                        response = self.env['res.company'].search([], limit=1).put('issue/' + help_tict_id.jira_id,
                                                                                   tags_remove_dict)

                        # send current tags to jira
                        tags_post_dict = {'update': {'labels': ''}}
                        tags_list = []

                        for tag in help_tict_id.tag_ids:
                            tag_dict = dict()
                            tag_dict['add'] = tag.name
                            tags_list.append(tag_dict)
                            help_tict_id.jira_tag_ids = [(4, tag.id)]  # update sync list

                        tags_post_dict['update']['labels'] = tags_list

                        _logger.info(f'TAGS LIST: {tags_list}')
                        _logger.info(f'TAGS POST DICT: {tags_post_dict}')

                        response = self.env['res.company'].search([], limit=1).put('issue/' + help_tict_id.jira_id,
                                                                                   tags_post_dict)
                    # ============================= ADDED PART =============================

        except Exception as e:
            _logger.info(f'EXCEPTION: {e}')
            raise Warning("You selected status, which is not available in jira..")
