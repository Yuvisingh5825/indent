{
    'name': 'Indent Management',
    'version': '19.0.1.0.0',
    'category': 'Purchase',
    'summary': 'Indent Process with Approval and Procurement',
    'description': """
Indent Management
=================
Create purchase indents, route them through a department-wise approval
workflow, raise and compare RFQs, and convert the selected RFQ into a
purchase order. Includes product demand and demand-by-destination reports.
    """,
    'author': 'Neemkaroli Consulting LLP',
    'website': 'https://your-website.com',
    'license': 'LGPL-3',
    'depends': ['base', 'mail', 'stock', 'purchase', 'hr', 'account'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/sequence.xml',
        'report/rfq_report.xml',
        'data/rfq_mail_template.xml',
        'views/indent_request_views.xml',
        'views/rfq_comparison_views.xml',
        'views/indent_request_search.xml',
        'views/product_demand_report_wizard_view.xml',
        'views/product_demand_tree_view.xml',
        'views/demand_by_destination_views.xml',
        'views/menu.xml',
        'wizard/indent_reject_wizard_view.xml',
    ],
    'images': ['static/description/banner.png'],
    'application': True,
    'installable': True,
}
