# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
        'name': 'Plan de Cuentas para la empresas Venezolanas',
        'author': 'Soluciones SoftHard',
        'category': 'Localization',
        'depends': ['account', 'l10n_ve_fiscal_requirements'],
        'data': [
                    'data/currency_data.xml',
                    'data/l10n_ve_chart_data.xml',
                    'data/account.account.template.csv',
                    'data/l10n_ve_chart_post_data.xml',
                    'data/account_data.xml',
                    'data/account_tax_data.xml',
                    'data/account_chart_template_data.xml',

            ],
}
