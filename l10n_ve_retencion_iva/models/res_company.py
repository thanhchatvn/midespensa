# -*- coding: utf-8 -*-

from odoo import api, fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    #Columns
    purchase_iva_ret_account = fields.Many2one('account.account', string='Cuenta de retención IVA proveedor')
    sale_iva_ret_account = fields.Many2one('account.account', string='Cuenta de declaracion IVA Cliente')
