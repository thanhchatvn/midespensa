# -*- coding: utf-8 -*-

{
    'name': 'Pos price checker',
    'version': '1.0',
    'category': 'Point of Sale',
    'sequence': 6,
    'author': 'Webveer',
    'summary': 'Allows customer to check product price.',
    'description': """

=======================
Allows customer to check product price.

""",
    'depends': ['point_of_sale'],
    'data': [
            'views/template.xml',
            'views/views.xml'
    ],
    'qweb': [
        'static/src/xml/pos.xml',
    ],
    'images': [
        'static/description/sele.jpg',
    ],
    'installable': True,
    'website': '',
    'auto_install': False,
    'price': 100,
    'currency': 'EUR',
}
