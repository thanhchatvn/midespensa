# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api


class PosConfig(models.Model):
    _inherit = 'pos.config'

    hka_printer = fields.Boolean(string='Printer HKA', help='Enable settings for HKA printers.')
    hka_printer_port = fields.Char(string='HKA Printer Port', help="Local Port address of an HKA receipt printer.")