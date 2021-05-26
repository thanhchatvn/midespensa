# -*- coding: utf-8 -*-
{
    "name": "Gestión de retenciones sobre IVA según las leyes venezolanas",
    "version": "1.1",
    "author": "Soluciones SoftHard",
    "license": "AGPL-3",
    "website": "http://www.solucionesofthard.com/",
    "category": 'Generic Modules/Accounting',
    "depends": ['base','account','l10n_ve_account_SH','l10n_ve_fiscal_requirements'],
    'data': [
        'wizard/declare_pay_iva.xml',
        'wizard/wh_export_iva_txt.xml',
        'report/report.xml',
        'report/wh_iva_receipt_template.xml',
        'views/account_invoice_view.xml',
        'views/wh_iva_view.xml',
        'views/account_view.xml',
        'views/res_config_view.xml',
        'views/retention_IVA.xml',
        'security/ir.model.access.csv',
        'security/ir_rule.xml',
        'data/ir_sequence_data.xml',
        'data/fiscal_position_data.xml',

        # ~ 'data/wh_mail_template_data.xml',
    ],
    'installable': True,
}
