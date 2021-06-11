# -*- coding: utf-8 -*-
from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    percentage_subtracting_1 = fields.Float('Subtracting 1%', related='company_id.percentage_subtracting_1')
    percentage_subtracting_3 = fields.Float('Subtracting 3%', related='company_id.percentage_subtracting_3')
    retention_islr_account_id = fields.Many2one('account.account',
                                                related='company_id.purchase_islr_ret_account_id',
                                                help="Account for defects for the retention of the IVA Suplier",
                                                readonly=False)
    sale_islr_ret_account_id = fields.Many2one('account.account',
                                               related='company_id.sale_islr_ret_account_id',
                                               help="Account for defects for the retention of the IVA Customer",
                                               readonly=False)

    tax_unit = fields.Float('Tax Unit', related='company_id.tax_unit', readonly=False, required=True)

    table_islr_id = fields.Many2one('account.withholding.rate.table', string='ISLR Table',
                                    related='company_id.table_islr_id', required=True, readonly=False)
