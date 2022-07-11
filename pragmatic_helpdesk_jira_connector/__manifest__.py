{
    'name': 'Pragmatic Helpdesk Jira Connector',
    'version': '14.0.1.0.5',
    'author': 'Pragmatic TechSoft Pvt Ltd.',
    'website': 'http://www.pragtech.co.in',
    'summary': 'Pragmatic Jira Connector',
    'description': """
    Helpdesk Jira Connector
    =======================================
    
    This connector will help user to import/export following objects in Jira.
    * Project
    * Task (Issues)
    * user
    * Attachments
    * Messages
    <keywords>
odoo jira odoo connector jira connector odoo task bug jira task issue
    """,
    'depends': ['helpdesk', 'project', 'hr'],
    'data': [
        'security/ir.model.access.csv',
        'security/security.xml',
        'data/data.xml',
        'views/res_company_views.xml',
        'views/project_views.xml',
        'views/helpdesk_ticket.xml',
        'wizards/message_view.xml',
    ],
    'images': ['static/description/odoo_jira_helpdesk.gif'],
    'live_test_url': 'https://www.pragtech.co.in/company/proposal-form.html?id=103&name=odoo-jira-connector',
    'price': 150,
    'currency': 'EUR',
    'license': 'OPL-1',
    'auto_install': False,
    'installable': True,
    'application': True,

}
