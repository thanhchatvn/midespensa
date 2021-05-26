# -*- coding: utf-8 -*-
#############################################################################
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
from odoo import models, fields, api
from odoo.exceptions import ValidationError

class AccountInvoice(models.Model):
    _inherit = 'account.move'

    vendor_invoice_number = fields.Char(string='Nro factura proveedor', readonly=True,
        states={'draft': [('readonly', False)]}, copy=False,
        help='El número de factura generado por el proveedor' )
    control_invoice_number = fields.Char(string='Nro de Control', readonly=True,
        states={'draft': [('readonly', False)]}, copy=False,
        help='Nro de control de la factura de proveedor', required=False)
    transaction_type = fields.Selection(([('01-reg','Registro'),
                                          ('02-complemento', 'Complemento'),
                                          ('03-anulacion', 'Anulación'),
                                          ('04-ajuste', 'Ajuste')]), string='Transaction Type', readonly=False,
                                            states={'draft': [('readonly', False)]},
                                            help='This is transaction type', compute='_compute_transaction_type')
    ajust_date = fields.Date(string='Fecha de Ajuste',readonly=False,
                                            states={'draft': [('readonly', False)]})

    @api.depends('type', 'state')
    def _compute_transaction_type(self):
        for move in self:
            if move.type in ('out_refund','in_refund') and move.state != 'cancel':
                move.transaction_type = '02-complemento'
            elif move.state == 'cancel':
                move.transaction_type = '03-anulacion'
            else:
                move.transaction_type = '01-reg'

    @api.constrains('control_invoice_number')
    def _check_control_number(self):
        records = self.env['account.move']
        if self.control_invoice_number:
            invoice_exist = records.search_count([('control_invoice_number', '=', self.control_invoice_number),('id', '!=', self.id),('type','in',('out_refund','out_invoice'))])
            if invoice_exist > 0 and self.type in ('out_refund','out_invoice'):
                raise ValidationError(("Ya existe una factura con este Número de Control"))
            else:
                return True