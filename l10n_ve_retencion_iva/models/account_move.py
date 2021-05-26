# -*- coding: utf-8 -*-
#############################################################################
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published
#    by the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
###############################################################################

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.addons import decimal_precision as dp
from odoo.tools.misc import formatLang, format_date, get_lang



class AccountInvoice(models.Model):
    _inherit = 'account.move'
    
    @api.depends('invoice_line_ids.price_subtotal','wh_id','wh_id.wh_lines','retention', 'amount_wh_iva', 'currency_id', 'company_id', 'invoice_date', 'type')
    def _compute_wh_iva(self):
        amount_iva = 0.0
        for invoice in self:
            if invoice.wh_id:
                whl_ids = self.env['account.wh.iva.line'].search(
                    [
                        ('invoice_id', '=', invoice.id),
                    ]
                )
                amount_iva = sum(whl.ret_amount for whl in whl_ids)
                invoice.amount_wh_iva = round(amount_iva, 2)
            else:
                invoice.amount_wh_iva = 0.0

    def action_reverse(self):
        for move in self:
            if move.wh_id:
                move.state = 'draft'
                move.wh_id.unlink_lines()
                move.state = 'posted'
        return super(AccountInvoice, self).action_reverse()

    def name_get(self):
        #esto genera un ciclo infinito
        # if 'wh_id' in self._context.keys():
        #     return [(invoice.id, u'%s (N° %s)' % (invoice.number or "Factura de Proveedor", invoice.vendor_invoice_number)) for invoice in self]
        if self.wh_id:
            return [(invoice.id, u'%s (N° %s)' % (invoice.company_id.name or "Factura de Proveedor", invoice.vendor_invoice_number)) for invoice in self]
        return super(AccountInvoice, self).name_get()
    
    @api.depends('invoice_line_ids','invoice_line_ids.price_unit','invoice_line_ids.price_subtotal','exempt_amount', 'currency_id', 'company_id', 'invoice_date', 'type')
    def get_exempt_amount(self):
        amount = 0.0
        amount = sum(self.invoice_line_ids.filtered(lambda line: not line.tax_ids or sum(line.tax_ids.mapped('amount')) == 0).mapped('price_subtotal'))
        self.exempt_amount = amount

    #Columns
    wh_id = fields.Many2one('account.wh.iva', 'Retención IVA', copy = False,
        readonly=True)
    amount_wh_iva = fields.Monetary(string='Wh IVA Amount', copy = False, digits=dp.get_precision('Withhold'),
        readonly=True, store=True, compute='_compute_wh_iva', track_visibility='onchangue')
    exempt_amount = fields.Monetary(string='Exempt amount', copy = False, digits=dp.get_precision('Withhold'),
        readonly=True, compute='get_exempt_amount', track_visibility='always')
    retention = fields.Selection(([('01-sin','No Retention'),
                                            ('02-special', '75% special contributor'),
                                            ('03-ordinary', '100% contributor ordinary'),
                                            ]),string='% de retencion', compute='_compute_retention', store=True, readonly=False)

    @api.depends('partner_id', 'type', 'partner_id.property_account_position_id')
    def _compute_retention(self):
        for inv in self:
            if inv.type in ('out_invoice', 'out_refund', 'out_receipt'):
                inv.retention = self.partner_id.property_account_position_id.ret_IVA_sale
            else:
                inv.retention = self.partner_id.property_account_position_id.ret_IVA_purchase


    #este metodo no se ejecuta porque no existe en odoo-13, viene de odoo 10
    #revisar si puede ser _move_autocomplete_invoice_lines_create
    @api.model
    def finalize_invoice_move_lines(self, move_lines):
        for inv in self:
            wh_iva_ids = self.env['account.wh.iva.line'].search([('invoice_id', '=', inv.id )])
            if inv.type in ['in_invoice','out_invoice']:
                if wh_iva_ids:
                    round_curr = inv.currency_id.round
                    company_currency = inv.company_id.currency_id
                    diff_currency = inv.currency_id != company_currency
                    for wh in wh_iva_ids:
                        for i in move_lines:
                            if inv.type in ['in_invoice']:
                                if int(i[2]['account_id'])==inv.account_id.id:
                                    new_amount = round_curr(i[2]['credit'] - float("{0:.2f}".format(wh.ret_amount)))
                                    if inv.type in ['in_invoice']:
                                        i[2]['credit']=new_amount
                                    move_line_iva = {
                                                 'analytic_account_id': False, 
                                                 'tax_ids': False, 
                                                 'name': 'Retención '+str(wh.ret_tax.description), 
                                                 'analytic_tag_ids': False, 
                                                 'product_uom_id': False, 
                                                 'invoice_id': inv.id, 
                                                 'analytic_line_ids': [], 
                                                 'tax_line_id': False, 
                                                 'currency_id': inv.currency_id.id, 
                                                 'credit': round_curr(float("{0:.2f}".format(wh.ret_amount))), 
                                                 'product_id': False, 
                                                 'date_maturity':i[2]['date_maturity'] , 
                                                 'debit': False, 
                                                 'amount_currency': False, 
                                                 'quantity': 1.0, 
                                                 'partner_id': inv.partner_id.id, 
                                                 'account_id': inv.company_id.purchase_iva_ret_account.id
                                    }
                                    move_lines.append((0,0,move_line_iva))
                            else:
                                if inv.type in ['out_invoice']:
                                    if int(i[2]['account_id']) == inv.account_id.id:
                                        amount = round_curr(i[2]['debit'] - wh.ret_amount)
                                        if inv.type in ['out_invoice']:
                                            i[2]['debit'] = amount
                                        move_line_iva = {
                                                     'analytic_account_id': False, 
                                                     'tax_ids': False, 
                                                     'name': 'Retención '+str(wh.ret_tax.description), 
                                                     'analytic_tag_ids': False, 
                                                     'product_uom_id': False, 
                                                     'invoice_id': inv.id, 
                                                     'analytic_line_ids': [], 
                                                     'tax_line_id': False, 
                                                     'currency_id': inv.currency_id.id, 
                                                     'credit': False, 
                                                     'product_id': False, 
                                                     'date_maturity':i[2]['date_maturity'] , 
                                                     'debit': round_curr(wh.ret_amount), 
                                                     'amount_currency': False, 
                                                     'quantity': 1.0, 
                                                     'partner_id': inv.partner_id.id, 
                                                     'account_id': inv.company_id.sale_iva_ret_account.id
                                        }
                                        move_lines.append((0,0,move_line_iva))
                
            if (inv.type=='in_refund' and inv.wh_id):
                wh_line = self.env['account.wh.iva.line'].search([('invoice_id', '=', inv.id )])
                for line in wh_line: 
                    for ml in move_lines:
                        if int(ml[2]['account_id']) == inv.account_id.id:
                            new_amount = ml[2]['debit'] - line.ret_amount
                            ml[2]['debit'] = new_amount
                            move_line_iriva =   {
                                          'analytic_account_id': False, 
                                          'tax_ids': False, 
                                          'name': 'Retención '+str(line.ret_tax.description), 
                                          'analytic_tag_ids': False, 
                                          'product_uom_id': False, 
                                          'invoice_id': inv.id, 
                                          'analytic_line_ids': [], 
                                          'tax_line_id': False, 
                                          'currency_id': inv.currency_id.id,  
                                          'credit': False, 
                                          'product_id': False, 
                                          'date_maturity':ml[2]['date_maturity'] , 
                                          'debit': line.ret_amount, 
                                          'amount_currency': False, 
                                          'quantity': 1.0, 
                                          'partner_id': inv.partner_id.id, 
                                          'account_id': line.invoice_id.wh_id.account_id.id
                                                }   
                            move_lines.append((0,0,move_line_iriva))
            if (inv.type=='out_refund' and inv.wh_id):
                wh_line = self.env['account.wh.iva.line'].search([('invoice_id', '=', inv.refund_invoice_id.id )])
                for line in wh_line: 
                    for ml in move_lines:
                        if int(ml[2]['account_id']) == inv.account_id.id:
                            new_amount = ml[2]['credit'] - line.ret_amount
                            ml[2]['credit'] = new_amount
                            move_line_iriva =   {
                                          'analytic_account_id': False, 
                                          'tax_ids': False, 
                                          'name': 'Retención '+str(line.ret_tax.description), 
                                          'analytic_tag_ids': False, 
                                          'product_uom_id': False, 
                                          'invoice_id': inv.id, 
                                          'analytic_line_ids': [], 
                                          'tax_line_id': False, 
                                          'currency_id': inv.currency_id.id,  
                                          'credit': line.ret_amount,
                                          'product_id': False, 
                                          'date_maturity':ml[2]['date_maturity'] , 
                                          'debit': False,
                                          'amount_currency': False, 
                                          'quantity': 1.0, 
                                          'partner_id': inv.partner_id.id, 
                                          'account_id': line.invoice_id.wh_id.account_id.id
                                                }   
                            move_lines.append((0,0,move_line_iriva))
        return super(AccountInvoice, self).finalize_invoice_move_lines(move_lines)
    
    def action_post(self):
        for inv in self:
            if inv.wh_id:
                if inv.wh_id.state != 'confirmed':
                    raise UserError(_('Debe confirmar la retención IVA asociada antes de poder validar la factura.'))
                    return
        inv_open= super(AccountInvoice, self).action_post()
        for inv in self:
            if inv.wh_id:
                wh_line = self.env['account.wh.iva.line'].search([('invoice_id', '=', inv.id )])
                if wh_line:
                    for line in wh_line:
                        if line.state != 'annulled':
                            line.write({'move_id':inv.id, 'state':'withhold'})
        return inv_open

    def action_invoice_cancel(self):
       invoice_cancel= super(AccountInvoice, self).action_invoice_cancel()
       for inv in self:
           if inv.wh_id:
                if inv.wh_id.state in ['draft','confirmed','withhold']:
                    inv.wh_id.write({'state': 'draft'})
                    for whl in inv.wh_id.wh_lines:
                        if whl.invoice_id.id == inv.id:
                            whl.write({'state': 'draft'})
                else:
                    raise UserError(_('La factura está asociada a una retención IVA Declarada.'))
                    return
       return invoice_cancel

    @api.model
    def create_lines_retention(self, retention_id):
        '''
            Este metodo crea las lineas de retencion en asientos contables.
            candidate:      la linea de retencion
            line_base:   la linea base de proveedores o clientes
        '''
        create_method = self.env['account.move.line'].with_context(check_move_validity=False).create
        line_base = self.line_ids.filtered(lambda line: line.account_id.user_type_id.type in ('receivable', 'payable'))
        account_ret = self.company_id.sale_iva_ret_account.id if self.type in ('out_invoice', 'out_refund', 'out_receipt') else self.company_id.purchase_iva_ret_account.id

        monto_iva_retenido = 0

        if self.currency_id.id:
            total_retenido = self.currency_id._convert(retention_id.total_tax_ret, self.company_id.currency_id, self.company_id, self.date)
            monto_iva_retenido += total_retenido
        else:
            total_retenido = retention_id.total_tax_ret
            monto_iva_retenido += total_retenido

        candidate = create_method([{
            'name': 'Retención de IVA',
            # 'debit': retention_id.total_tax_ret if self.type in ('out_invoice', 'in_refund', 'out_receipt') else 0.0,
            'debit': monto_iva_retenido if self.type in ('out_invoice', 'in_refund', 'out_receipt') else 0.0,
            # 'credit': retention_id.total_tax_ret if self.type not in ('out_invoice', 'in_refund', 'out_receipt') else 0.0,
            'credit': monto_iva_retenido if self.type not in ('out_invoice', 'in_refund', 'out_receipt') else 0.0,
            'quantity': 1.0,
            'date_maturity': fields.Date.context_today(self),
            'move_id': self.id,
            'currency_id': self.currency_id.id if self.currency_id != self.company_id.currency_id else False,
            'amount_currency': self._amount_currency(self.amount_wh_iva),
            'account_id': account_ret,
            'partner_id': self.commercial_partner_id.id,
            'exclude_from_invoice_tab': True,
        }])
        line_base.with_context(check_move_validity=False).write({
            # 'credit': line_base['credit'] - retention_id.total_tax_ret if self.type not in ('out_invoice', 'in_refund', 'out_receipt') else 0.0,
            'credit': line_base['credit'] - monto_iva_retenido if self.type not in ('out_invoice', 'in_refund', 'out_receipt') else 0.0,
            # 'debit': line_base['debit'] - retention_id.total_tax_ret if self.type in ('out_invoice', 'in_refund', 'out_receipt') else 0.0,
            'debit': line_base['debit'] - monto_iva_retenido if self.type in ('out_invoice', 'in_refund', 'out_receipt') else 0.0,
        })
        candidate._onchange_balance()

    def _amount_currency(self, amount_wh_iva):
        """
        metedo que realiza para la ver cambio de la moneda
        :param amount_wh_iva:
        :return:
        """
        if self.type in ('out_invoice', 'in_refund', 'out_receipt'):
            amount_wh_iva = amount_wh_iva
        elif self.type not in ('out_invoice', 'in_refund', 'out_receipt'):
            amount_wh_iva = amount_wh_iva * -1
        else:
            amount_wh_iva = 0.0
        return amount_wh_iva

    def action_confirm_retention(self):
        self.wh_id.action_confirm()

    # def print_wh_iva(self):
    #     # self.env['account.wh.iva'].search([('id', '=', self.wh_id.id)]).print_wh_iva_receipt()
    #     wh_iva = self.env['account.wh.iva'].search([('id', '=', self.wh_id.id)])
    #     return wh_iva.env.ref(wh_iva.id, 'l10n_ve_retencion_iva.wh-iva_receipt_document')

    def print_wh_iva(self):
        self.ensure_one()
        iva = self.env['account.wh.iva'].search([('id', '=', self.wh_id.id)])
        return self.env['account.wh.iva'].search([('id', '=', self.wh_id.id)]).env.ref('l10n_ve_retencion_iva.report_withholding_receipt').report_action(iva)

    def action_post(self):
        '''
        Este metodo se usa para confirmar la retenciones a la hora de publicar la factura.
        :return:
        '''
        if self.wh_id:
            self.create_lines_retention(self.wh_id)
            self.wh_id.action_confirm()
        res = super(AccountInvoice, self).action_post()
        return res

    def button_draft(self):
        for move in self:
            res = super(AccountInvoice, self).button_draft()
            if move.wh_id:
                move.wh_id.state = 'draft'
                move.wh_id.unlink_lines()
        return res

    def create_retention(self):
        '''
            Este metodo crea la retencion a partir de un boton
        '''
        if not self.amount_by_group:
            raise UserError(_('No se puede crear una retención a una factura sin impuestos asociados.'))
        if self.wh_id:
            raise UserError(_('Ya existe una retención para esta factura. Por favor eliminela, antes de crear otra.'))
            return
        if self.retention == '01-sin' or not self.retention:
            raise UserError(_('Esta factura no posee un porentage de Retención asociado.'))
            return
        amount_retention = 100.0 if self.retention == '03-ordinary' else 75.0 if self.retention == '02-special' else 0

        #se definen las cuentas por defecto para la retencion
        type_tax_use = 'purchase'
        if self.type in ('out_invoice', 'out_refund', 'out_receipt'):
            account_ret = self.company_id.purchase_iva_ret_account.id
            type_tax_use = 'sale'
        else:
            account_ret = self.company_id.sale_iva_ret_account.id

        #valores de los campos de retencion de iva en el modelo account.wh.iva
        wh_lines = []
        for group in self._compute_invoice_taxes_by_group_iva_l10nve():
            tax = self.env['account.tax'].search([
                ('tax_group_id', '=', group[6]),
                ('company_id', '=', self.company_id.id),
                ('type_tax_use', '=', type_tax_use),
            ])
            amount_tax = group[1]
            invoice_line = self.line_ids.filtered(lambda line: line.tax_line_id.id == tax.id)
            wh_lines.append((0, False, {
                    'invoice_id': self.id,
                    'base_tax': group[2],
                    'rate_amount': float(amount_retention),
                    'ret_tax': tax.id,
                    'amount_tax': amount_tax,
                    'ret_amount': (amount_retention * amount_tax) / 100,
                    'payments_three': invoice_line.payments_three or False
                }
            ))
        
        vals = {
            'company_id': self.company_id.id,
            'partner_id': self.partner_id.id,
            'journal_id': self.journal_id.id,
            'account_id': account_ret,
            'date': self.date,
            'type': self.type,
            'refund': True if self.type in ('in_refund', 'out_refund') else False,
            'wh_lines': wh_lines
        }
        retention_id = self.env['account.wh.iva'].create(vals)
        self.wh_id = retention_id.id

    def _compute_invoice_taxes_by_group_iva_l10nve(self):
        ''' Helper to get the taxes grouped according their account.tax.group.
            This method is only used when printing the invoice.
        '''
        taxes = self.invoice_line_ids.mapped('tax_ids')  # Line receives taxes
        lines = self.invoice_line_ids.filtered(lambda line: line.tax_ids)
        done_taxes = set()
        res = {}

        for move in self:
            lang_env = move.with_context(lang=move.partner_id.lang).env
            tax_lines = move.line_ids.filtered(lambda line: line.tax_line_id)
            tax_balance_multiplicator = -1 if move.is_inbound(True) else 1

            for i in tax_lines:
                res.setdefault(i.tax_line_id.tax_group_id, {'base': 0.0, 'amount': 0.0})
                res[i.tax_line_id.tax_group_id]['amount'] += tax_balance_multiplicator * (i.amount_currency if i.currency_id else i.balance)

            for tax in taxes:  # Itera for taxes
                line = lines.search([('tax_ids', 'in', tax.id),('move_id', '=', self.id)])  # get taxes from invoice line
                for price in line:
                    res.setdefault(price.tax_ids.tax_group_id, {'base': 0.0, 'amount': 0.0})
                    tax_key_add_base = tuple([price.id])
                    if tax_key_add_base not in done_taxes:
                        price_subtotal = price.price_subtotal
                    else:
                        pass
                    res[price.tax_ids.tax_group_id]['base'] += price_subtotal  # At the baseline it saves me the price of the subtotal
                    done_taxes.add(tax_key_add_base)

            res = sorted(res.items(), key=lambda l: l[0].sequence)
            move.amount_by_group = [(
                group.name,
                amounts['amount'],
                amounts['base'],
                formatLang(lang_env, amounts['amount'], currency_obj=move.currency_id),
                formatLang(lang_env, amounts['base'], currency_obj=move.currency_id),
                len(res),
                group.id
            ) for group, amounts in res]
            amount_by_group_2 = move.amount_by_group
        return amount_by_group_2

    def delete_retention(self):
        self.env['account.wh.iva'].search([('id', '=', self.wh_id.id)]).unlink()

    def write(self, vals):
        value = {}
        wh_iva_line_obj = self.env['account.wh.iva.line']
        for inv in self:
            if 'wh_id' in vals.keys():
                # if not vals['wh_id']:
                #     self.env['account.wh.iva.line'].search([('invoice_id', '=', inv.id )]).unlink()
                if vals['wh_id']:
                    wh_iva = self.env['account.wh.iva'].search([('id', '=', int(vals['wh_id']))])
                    wh_iva_line_ids = wh_iva_line_obj.search([('invoice_id', '=', inv.id)])
                    value = {'invoice_id': inv.id,
                            'retention_id':  wh_iva.id,
                            'ret_tax':  inv.invoice_line_ids.tax_ids,
                            'base_tax': inv.amount_untaxed,
                            'amount_tax': inv.amount_total,
                            'rate_amount': 100.00 if inv.retention =='03-ordinary' else 75.0 if inv.retention=='02-special' else 0,}
                    if not wh_iva_line_ids:
                        wh_iva_line_obj.create(value)
                    else:
                        for wh_line in wh_iva_line_ids:
                            if wh_line.retention_id.id != int(vals['wh_id']):
                                wh_line.unlink()
                                wh_iva_line_obj.create(value)
        invoice =  super(AccountInvoice, self).write(vals)
        for wh in self:
            if wh.wh_id:
                if 'invoice_line_ids' in vals.keys() or 'retention' in vals.keys():
                    wh_line_ids = wh_iva_line_obj.search([('invoice_id', '=', inv.id)])
                    if wh_line_ids:
                        for whl in wh_line_ids:
                            whl.state='draft'
                            whl.unlink()
                        [wh_line_ids.create({
                                'retention_id':wh.wh_id.id,
                                'invoice_id': wh.id,
                                'ret_tax':  tax_id.tax_id.id,
                                'base_tax': tax_id.base,
                                'amount_tax': tax_id.mapped('amount'),
                                'rate_amount': 100.00 if inv.retention=='03-ordinary' else 75.0 if inv.retention=='02-special' else 0,
                            }) for tax_id in wh.invoice_line_ids.tax_ids if tax_id.amount > 0]
                        wh_line_new = wh_iva_line_obj.search([('invoice_id', '=', inv.id)])
                        if wh_line_new:
                            for whln in wh_line_new:
                                whln.state = whln.retention_id.state
        return invoice


class AccountMoveLineInherit(models.Model):
    _inherit = "account.move.line"
    
    pay_wh_id = fields.Many2one('account.wh.iva.pay', 'Withholding IVA', 
                                    readonly=True, 
                                    copy=False)

    payments_three = fields.Boolean(string='Payments to third parties', default=False)


# ~ class AccountInvoiceRefundIva(models.TransientModel):
    # ~ """Refunds invoice"""

    # ~ _inherit = "account.invoice.refund"
                                    
    # ~ @api.model
    # ~ def invoice_refund(self):
        # ~ invoice_refund = super(AccountInvoiceRefundIva, self).invoice_refund()
        # ~ inv_obj = self.env['account.invoice']
        # ~ context = dict(self._context or {})
        # ~ for inv in inv_obj.browse(context.get('active_ids')):
            # ~ if inv.wh_id:
                # ~ inv.wh_id.wh_refund_invoice(inv.id)
        # ~ return invoice_refund
    
