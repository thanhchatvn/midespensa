
{
    "name": """POS: show dual currency""",
    "summary": """Adds price  of other currency at products in POS""",
    "category": "Point Of Sale",
    "version": "13.0.1.0.0",
    "application": False,
    'author': 'José Luis Vizcaya López',
    'company': 'José Luis Vizcaya López',
    'maintainer': 'José Luis Vizcaya López',
    'website': 'https://github.com/birkot',
    "depends": ["point_of_sale", "stock"],
    "data": ["views/data.xml", "views/views.xml"],
    "qweb": ["static/src/xml/pos.xml"],
    "license": "OPL-1",
    'images': [
        'static/description/thumbnail.png',
    ],
    "price": 10,
    "currency": "USD",
    "auto_install": False,
    "installable": True,
}
