# -*- coding: utf-8 -*-
{
    "name": "Gestión de Retenciones de impuestos sobre la renta según las leyes venezolanas",
    "version": "1.1",
    "author": "Soluciones SoftHard",
    "license": "AGPL-3",
    "website": "http://www.solucionesofthard.com",
    "category": 'Generic Modules/Accounting',
    "depends": ["base","account","l10n_ve_account_SH","l10n_ve_fiscal_requirements"],
    'data': [
        'security/ir.model.access.csv',
        'security/ir_rule.xml',
        'data/account.withholding.concept.csv',
        'data/account.withholding.rate.table.csv',
        'data/account.withholding.rate.table.line.csv',
        'data/ir_sequence_data.xml',
        'wizard/payment_islr_wizard.xml',
        'wizard/message_warning.xml',
        'views/wh_islr_view.xml',
        'views/res_config_settings.xml',
        'views/ret_product_islr.xml',
        'views/button_islr_view.xml',
        'views/wh_islr_rate_table_view.xml',
        'reports/report.xml',
        # 'reports/report_islr_template.xml',
        'reports/withholding_receipt_template.xml',
        # 'data/wh_mail_template_data.xml'
        # 'reports/report.xml',
        # 'reports/report_islr_template.xml',
        # 'reports/withholding_receipt_template.xml'
    ],
    'installable': True,
}

