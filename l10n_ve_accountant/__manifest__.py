# -*- coding: utf-8 -*-
{
    'name': "Libros Contables de Venezuela",
    'version': '0.1',
    'author': "Soluciones SoftHard",
    "license": "AGPL-3",
    "website": "http://www.solucionesofthard.com/",
    'category': 'Generic Modules/Accounting',
    'depends': [
        'base',
        'account',
        'l10n_ve_account_SH',
        'l10n_ve_fiscal_requirements',
        'l10n_ve_retencion_iva',
        'account_accountant',
    ],
    'data': [
        # 'security/ir.model.access.csv',
        'wizard/wizard_report_excel_view.xml',
        'wizard/wizard_book.xml',
        'wizard/wizard_sale_book_view.xml',
        'reports/report_shopping_book.xml',
        'reports/report_sales_book.xml',
        'views/account_move.xml'
    ],
}
