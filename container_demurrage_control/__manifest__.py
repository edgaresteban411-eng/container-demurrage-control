{
    'name': 'Container Demurrage Control',
    'version': '17.0.1.0.0',
    'category': 'Operations',
    'summary': 'Control and calculate container demurrage costs',
    'depends': ['base', 'mail'],
    'data': [
        'security/ir.model.access.csv',
        'views/demurrage_views.xml',
    ],
    'installable': True,
    'application': True,
}