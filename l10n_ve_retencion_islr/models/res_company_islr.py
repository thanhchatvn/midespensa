# -*- coding: utf-8 -*-

from odoo import api, fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    # Columns
    percentage_subtracting_1 = fields.Float('Subtracting 1%', compute='_compute_percentage_subtracting_1')
    percentage_subtracting_3 = fields.Float('Subtracting 3%', compute='_compute_percentage_subtracting_3')
    factor = fields.Float('Factor', related='table_islr_id.factor')
    purchase_islr_ret_account_id = fields.Many2one(comodel_name='account.account',
                                                   string='Cuenta de retención ISLR proveedor')
    sale_islr_ret_account_id = fields.Many2one(comodel_name='account.account',
                                               string='Cuenta de retención ISLR cliente')
    table_islr_id = fields.Many2one('account.withholding.rate.table', string='ISLR Table')
    tax_unit = fields.Float('Tax Unit')

    def _compute_percentage_subtracting_1(self):
        for percentage_1 in self:
            tax_unit = percentage_1.tax_unit
            factor = percentage_1.factor
            percentage_subtracting = tax_unit * factor * 0.01
            percentage_1.percentage_subtracting_1 = percentage_subtracting

    def _compute_percentage_subtracting_3(self):
        for percentage_3 in self:
            tax_unit = percentage_3.tax_unit
            factor = percentage_3.factor
            percentage_subtracting = tax_unit * factor * 0.03
            percentage_3.percentage_subtracting_3 = percentage_subtracting
