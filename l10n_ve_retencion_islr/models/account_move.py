# -*- coding: utf-8 -*-

from odoo import fields, models, api, _
from odoo.exceptions import UserError
from odoo.addons import decimal_precision as dp

class AccountMove(models.Model):
    _inherit = 'account.move'

    amount_residual = fields.Monetary(string='Amount Due', store=True,
                                      compute='_compute_amount')

    def _compute_amount(self):
        super(AccountMove, self)._compute_amount()
        if self.withholding_id:
            for move in self:
                new_total_residual = 0.0
                residual_currency = 0.0
                total_residual = 0.0
                total_residual_currency = 0.0
                currencies = set()
                for line in move.line_ids:
                    if line.currency_id:
                        currencies.add(line.currency_id)

                    if line.account_id.user_type_id.type in ('receivable', 'payable'):
                        total_residual += line.amount_residual
                        total_residual_currency += line.amount_residual_currency
                        residual_currency += move.amount_wh_islr if total_residual_currency < 0 else -move.amount_wh_islr
                        total_residual_currency = residual_currency

                    if move.type == 'entry' or move.is_outbound():
                        sign = 1
                    else:
                        sign = -1
                if len(currencies) == 1:
                    move.amount_residual += -sign * total_residual_currency
                else:
                    continue
            else:
                pass

    @api.depends('invoice_line_ids.price_subtotal', 'withholding_id.amount_total', 'withholding_id.withholding_line')
    def _compute_wh_islr(self):
        amount_iva = 0.0
        for invoice in self:
            invoice.amount_wh_islr = invoice.withholding_id.amount_total

    #Columns
    withholding_id = fields.Many2one('account.wh.islr', 'Withholding', readonly=True, copy=False)
    amount_wh_islr = fields.Monetary(string='Importe de retención de ISLR', copy=False, digits=dp.get_precision('Withhold'),
                                    readonly=True, store=True, compute='_compute_wh_islr', track_visibility='onchange')

    @api.model #Crea los apunte contables
    def create_lines_retentions(self, wh_islr_obj):
        monto_islr_retenido = 0

        if self.currency_id.id:
            total_retenido = self.currency_id._convert(wh_islr_obj.amount_total, self.company_id.currency_id, self.company_id, self.date)
            monto_islr_retenido += total_retenido
        else:
            total_retenido = wh_islr_obj.amount_total
            monto_islr_retenido += total_retenido

        create_methods = self.env['account.move.line'].with_context(check_move_validity=False).create
        if self.type == 'in_invoice':
            line_payables = self.line_ids.filtered(lambda lines: lines.account_id.user_type_id.type == 'payable')
            candidates = create_methods([{
                'name': 'Retención de ISLR',
                'debit': 0,
                # 'credit': wh_islr_obj.amount_total,
                'credit': monto_islr_retenido,
                'quantity': 1.0,
                # 'amount_currency': ,
                'date_maturity': fields.Date.context_today(self),
                'move_id': self.id,
                'currency_id': self.currency_id.id if self.currency_id != self.company_id.currency_id else False,
                'amount_currency': self._amount_currency(self.amount_wh_islr),
                'account_id': self.company_id.purchase_islr_ret_account_id.id,
                'partner_id': self.commercial_partner_id.id,
                'exclude_from_invoice_tab': True,
            }])
            line_payables.with_context(check_move_validity=False).write(
                # {'credit': line_payables['credit'] - wh_islr_obj.amount_total})
                {'credit': line_payables['credit'] - monto_islr_retenido})
        elif self.type == 'out_invoice':
            line_payables = self.line_ids.filtered(lambda lines: lines.account_id.user_type_id.type == 'receivable')
            candidates = create_methods([{
                'name': 'ISLR Retenido por CLiente',
                # 'debit': wh_islr_obj.amount_total,
                'debit': monto_islr_retenido,
                'credit': 0,
                'quantity': 1.0,
                # 'amount_currency': ,
                'date_maturity': fields.Date.context_today(self),
                'move_id': self.id,
                'currency_id': self.currency_id.id if self.currency_id != self.company_id.currency_id else False,
                'amount_currency': self._amount_currency(self.amount_wh_islr),
                'account_id': self.company_id.sale_islr_ret_account_id.id,
                'partner_id': self.commercial_partner_id.id,
                'exclude_from_invoice_tab': True,
            }])
            line_payables.with_context(check_move_validity=False).write(
                # {'debit': line_payables['debit'] - wh_islr_obj.amount_total})
                {'debit': line_payables['debit'] - monto_islr_retenido})
        elif self.type == 'in_refund':
            line_payables = self.line_ids.filtered(lambda lines: lines.account_id.user_type_id.type == 'payable')
            candidates = create_methods([{
                'name': 'Retención de ISLR',
                # 'debit': wh_islr_obj.amount_total,
                'debit': monto_islr_retenido,
                'credit': 0,
                'quantity': 1.0,
                # 'amount_currency': ,
                'date_maturity': fields.Date.context_today(self),
                'move_id': self.id,
                'currency_id': self.currency_id.id if self.currency_id != self.company_id.currency_id else False,
                'amount_currency': self._amount_currency(self.amount_wh_islr),
                'account_id': self.company_id.sale_islr_ret_account_id.id,
                'partner_id': self.commercial_partner_id.id,
                'exclude_from_invoice_tab': True,
            }])
            line_payables.with_context(check_move_validity=False).write(
                # {'debit': line_payables['debit'] - wh_islr_obj.amount_total})
                {'debit': line_payables['debit'] - monto_islr_retenido})
        elif self.type == 'out_refund':
            line_payables = self.line_ids.filtered(lambda lines: lines.account_id.user_type_id.type == 'payable')
            candidates = create_methods([{
                'name': 'Retención de ISLR',
                'debit': 0,
                # 'credit': wh_islr_obj.amount_total,
                'credit': monto_islr_retenido,
                'quantity': 1.0,
                # 'amount_currency': ,
                'date_maturity': fields.Date.context_today(self),
                'move_id': self.id,
                'currency_id': self.currency_id.id if self.currency_id != self.company_id.currency_id else False,
                'amount_currency': self._amount_currency(self.amount_wh_islr),
                'account_id': self.company_id.purchase_islr_ret_account_id.id,
                'partner_id': self.commercial_partner_id.id,
                'exclude_from_invoice_tab': True,
            }])

            line_payables.with_context(check_move_validity=False).write(
                # {'credit': line_payables['credit'] - wh_islr_obj.amount_total})
                {'credit': line_payables['credit'] - monto_islr_retenido})
        candidates._onchange_balance()

    def _amount_currency(self, amount_wh_islr):
        """
        metedo que realiza para la ver cambio de la moneda
        :param amount_wh_islr:
        :return:
        """
        if self.type in ('out_invoice', 'in_refund', 'out_receipt'):
            amount_wh_islr = amount_wh_islr
        elif self.type not in ('out_invoice', 'in_refund', 'out_receipt'):
            amount_wh_islr = amount_wh_islr * -1
        else:
            amount_wh_islr = 0.0
        return amount_wh_islr

    #Crea la retencion
    def create_retentions(self):
        lines = []
        retention_bs = 0
        valss_retention = {}
        if self.type == 'in_invoice':
            for line in self.invoice_line_ids:
                wh_table_retention_line = line.get_islr_retentions_dates()
                if not wh_table_retention_line:
                    return {
                        'name': _('Advertencia !'),
                        'res_model': 'message.islr.warning',
                        'type': 'ir.actions.act_window',
                        'view_mode': 'form',
                        'view_type': 'form',
                        'context': {'default_warning': _('No se encontraron valores para la generación de retención de ISLR. Debera generarla de forma manual')},
                        'target':'new'
                    }
                if wh_table_retention_line.rate2:
                    ut = line.company_id.tax_unit
                    base = float(line.debit) if line.move_id.currency_id else float(line.move_id.amount_untaxed)
                    # amount_base = float(line.debit * wh_table_retention_line.percentage_amount_base / 100)
                    amount_base = float(base * wh_table_retention_line.percentage_amount_base / 100)
                    unit_amount_base = amount_base / ut
                    rate2_ids = wh_table_retention_line.table_id.rate2_ids.search([('lower_limit', '<=', unit_amount_base),
                                                                                   '|',
                                                                                   ('upper_limit', '>=', unit_amount_base),
                                                                                   ('upper_limit', '=', 0)])
                    result_a = float(unit_amount_base * rate2_ids.percentage / 100)
                    retention_ut = float(result_a - rate2_ids.subtracting)
                    retention_no_bs = float(retention_ut * ut)
                    # retention_bs = float(retention_ut * ut)
                    retention_bs = line.move_id.company_id.currency_id._convert(retention_no_bs, line.move_id.currency_id,
                                                          line.move_id.company_id, line.move_id.date) if line.move_id.currency_id else float(retention_ut * ut)
                # amount_base = float(line.debit * wh_table_retention_line.percentage_amount_base/100)
                amount_base = float(line.move_id.amount_untaxed * wh_table_retention_line.percentage_amount_base/100)
                ret_amount = float(amount_base * wh_table_retention_line.percentage/100)
            lines.append([0, False, {
                'invoice_id': self.id,  # factura
                'amount_invoice': self.amount_total,
                'base_tax': self.amount_untaxed,
                'porc_islr': wh_table_retention_line.percentage,
                'code_withholding_islr': wh_table_retention_line.code,
                'descripcion': wh_table_retention_line.concept.name,
                'ret_amount': ret_amount if not wh_table_retention_line.rate2 else retention_bs
            }])
            valss_retention = {
                'name': self.name,
                'partner_id': self.partner_id.id,
                'journal_id': self.journal_id.id,
                'date': self.date,
                'company_id': self.company_id.id,
                'account_id': self.company_id.purchase_islr_ret_account_id.id,
                # 'type':self.search[('type', '=', 'in_invoice')],
                'withholding_line': lines,
             }
        elif self.type == 'out_invoice':
            for line in self.invoice_line_ids:
                wh_table_retention_line = line.get_islr_retentions_dates()
                amount_base = float(line.credit * wh_table_retention_line.percentage_amount_base / 100)
                ret_amount = float(amount_base * wh_table_retention_line.percentage / 100)
            lines.append([0, False, {
                'invoice_id': self.id,  # factura
                'amount_invoice': self.amount_total,
                'base_tax': self.amount_untaxed,
                'porc_islr': wh_table_retention_line.percentage,
                'code_withholding_islr': wh_table_retention_line.code,
                'descripcion': wh_table_retention_line.concept.name,
                'ret_amount': ret_amount
            }])
            valss_retention = {
                'name': self.name,
                'partner_id': self.partner_id.id,
                'journal_id': self.journal_id.id,
                'date': self.date,
                'company_id': self.company_id.id,
                'account_id': self.company_id.sale_islr_ret_account_id.id,
                'withholding_line': lines,
            }
        elif self.type == 'out_refund':
            for line in self.invoice_line_ids:
                wh_table_retention_line = line.get_islr_retentions_dates()
                # if not wh_table_retention_line:
                #     return {
                #         'name': _('Advertencia !'),
                #         'res_model': 'message.islr.warning',
                #         'type': 'ir.actions.act_window',
                #         'view_mode': 'form',
                #         'view_type': 'form',
                #         'context': {'default_warning': _('No se encontraron valores para la generación de retención de ISLR. Debera generarla de forma manual')},
                #         'target':'new'
                #     }
                amount_base = float(line.debit * wh_table_retention_line.percentage_amount_base / 100)
                ret_amount = float(amount_base * wh_table_retention_line.percentage / 100)
            lines.append([0, False, {
                'invoice_id': self.id,  # factura
                'amount_invoice': self.amount_total,
                'base_tax': self.amount_untaxed,
                'porc_islr': wh_table_retention_line.percentage,
                'code_withholding_islr': wh_table_retention_line.code,
                'descripcion': wh_table_retention_line.concept.name,
                'ret_amount': ret_amount
            }])
            valss_retention = {
                'name': self.name,
                'partner_id': self.partner_id.id,
                'journal_id': self.journal_id.id,
                'date': self.date,
                'company_id': self.company_id.id,
                'account_id': self.company_id.sale_islr_ret_account_id.id,
                'withholding_line': lines,
            }
        elif self.type == 'in_refund':
            for line in self.invoice_line_ids:
                wh_table_retention_line = line.get_islr_retentions_dates()
                if not wh_table_retention_line:
                    return {
                        'name': _('Advertencia !'),
                        'res_model': 'message.islr.warning',
                        'type': 'ir.actions.act_window',
                        'view_mode': 'form',
                        'view_type': 'form',
                        'context': {'default_warning': _('No se encontraron valores para la generación de retención de ISLR. Debera generarla de forma manual')},
                        'target':'new'
                    }
                if wh_table_retention_line.rate2:
                    ut = line.company_id.tax_unit
                    base = float(line.credit) if line.move_id.currency_id else float(line.move_id.amount_untaxed)
                    amount_base = float(base * wh_table_retention_line.percentage_amount_base / 100)
                    unit_amount_base = amount_base / ut
                    rate2_ids = wh_table_retention_line.table_id.rate2_ids.search(
                        [('lower_limit', '<=', unit_amount_base),
                         '|',
                         ('upper_limit', '>=', unit_amount_base),
                         ('upper_limit', '=', 0)])
                    result_a = float(unit_amount_base * rate2_ids.percentage / 100)
                    retention_ut = float(result_a - rate2_ids.subtracting)
                    retention_no_bs = float(retention_ut * ut)
                    # retention_bs = float(retention_ut * ut)
                    retention_bs = line.move_id.company_id.currency_id._convert(retention_no_bs,
                                                                                line.move_id.currency_id,
                                                                                line.move_id.company_id,
                                                                                line.move_id.date) if line.move_id.currency_id else float(
                        retention_ut * ut)
                amount_base = float(line.move_id.amount_untaxed * wh_table_retention_line.percentage_amount_base / 100)
                ret_amount = float(amount_base * wh_table_retention_line.percentage / 100)
            lines.append([0, False, {
                'invoice_id': self.id,  # factura
                'amount_invoice': self.amount_total,
                'base_tax': self.amount_untaxed,
                'porc_islr': wh_table_retention_line.percentage,
                'code_withholding_islr': wh_table_retention_line.code,
                'descripcion': wh_table_retention_line.concept.name,
                'ret_amount': ret_amount if not wh_table_retention_line.rate2 else retention_bs
            }])
            valss_retention = {
                'name': self.name,
                'partner_id': self.partner_id.id,
                'journal_id': self.journal_id.id,
                'date': self.date,
                'company_id': self.company_id.id,
                'account_id': self.company_id.sale_islr_ret_account_id.id,
                'withholding_line': lines,
            }
        wh_islr_obj = self.env['account.wh.islr']
        result = wh_islr_obj.create(valss_retention)
        self.withholding_id = result.id


    def action_post(self):
        '''
        Este metodo se usa para confirmar la retenciones a la hora de publicar la factura.
        :return:
        '''
        if self.withholding_id.number  != False:
            self.withholding_id.action_confirm_2()
            self.create_lines_retentions(self.withholding_id)  # Crea los apuntes contables de retencion de islr
            return super(AccountMove, self).action_post()
        elif self.withholding_id:
            self.withholding_id.action_confirm()
            self.create_lines_retentions(self.withholding_id)  # Crea los apuntes contables de retencion de islr
        res = super(AccountMove, self).action_post()
        return res

    def button_draft(self):
        '''
        Este metodo se usa para pasar las retenciones a borrador cuando se pasa la factura de publicado a borrador (ISLR)
        :return:
        '''
        for hw in self:
            res = super(AccountMove, self).button_draft()
            if hw.withholding_id.withholding_line.state == 'confirmed':
                hw.withholding_id.write({'state': 'draft'})
                hw.withholding_id.withholding_line.write({'state': 'draft'})
                hw.unlink_liness()
            # else:
            #     raise UserError(_('Islr withholding is already declared.'))
        return res

    def unlink_liness(self):
        '''
            Este metodo se usa para borras las lineas de retenciones (ISLR)
            :return:
        '''
        for inv in self:
            lines_retent = inv.env['account.move.line']
            if inv.type in ('in_invoice','in_refund'):
                lines_retent = inv.env['account.move.line'].search(
                    [('account_id', '=', self.company_id.purchase_islr_ret_account_id.id),
                     ('move_id', '=', inv.id)])
                line_payables = inv.line_ids.filtered(
                    lambda line: line.account_id.user_type_id.type in ('payable'))
            elif inv.type in ('out_invoice','out_refund'):
                lines_retent = inv.env['account.move.line'].search(
                    [('account_id', '=', self.company_id.sale_islr_ret_account_id.id),
                     ('move_id', '=', inv.id)])
                line_payables = inv.line_ids.filtered(
                    lambda line: line.account_id.user_type_id.type == 'receivable')

            for line in lines_retent:
                line_payables.with_context(check_move_validity=False).write({
                    'credit': line_payables['credit'] + line['credit'] if self.type in (
                    'in_invoice') else 0.0,
                    'debit': line_payables['debit'] + line['debit'] if self.type not in (
                    'in_invoice') else 0.0,
                    })
            lines_retent.unlink()


    def print_withholding_receipt_xml(self): #Boton para crear el comprobante de retencion
        self.ensure_one()
        islr = self.env['account.wh.islr'].search([('id', '=', self.withholding_id.id)])
        return self.env['account.wh.islr'].search([('id', '=', self.withholding_id.id)]).env.ref(
            'l10n_ve_retencion_islr.account_withholding_receipt_report').report_action(islr)

    def delete_retentions(self):
        self.env['account.wh.islr'].search([('id', '=', self.withholding_id.id)]).unlink()
        # self.env['account.move'].search([('id', '=', self.line_ids.withholding_id)]).unlink()

        # (self.mapped('debit') + self.mapped('credit')).unlink()
        # return self.

    def _reverse_moves(self, default_values_list=None, cancel=False):
        '''
        Cuando se genere una nota de credito no trae los movimientos correspondientes a las retenciones (ISLR)
        :return:
        '''
        reverse_moves = super(AccountMove, self)._reverse_moves()
        reverse_moves.unlink_liness()
        return reverse_moves

    def _check_balanced(self):
        ''' Assert the move is fully balanced debit = credit.
        An error is raised if it's not the case.
        '''
        moves = self.filtered(lambda move: move.line_ids)
        if not moves:
            return

        # /!\ As this method is called in create / write, we can't make the assumption the computed stored fields
        # are already done. Then, this query MUST NOT depend of computed stored fields (e.g. balance).
        # It happens as the ORM makes the create with the 'no_recompute' statement.
        self.env['account.move.line'].flush(['debit', 'credit', 'move_id'])
        self.env['account.move'].flush(['journal_id'])
        self._cr.execute('''
               SELECT line.move_id, ROUND(SUM(debit - credit), currency.decimal_places)
               FROM account_move_line line
               JOIN account_move move ON move.id = line.move_id
               JOIN account_journal journal ON journal.id = move.journal_id
               JOIN res_company company ON company.id = journal.company_id
               JOIN res_currency currency ON currency.id = company.currency_id
               WHERE line.move_id IN %s
               GROUP BY line.move_id, currency.decimal_places
               HAVING ROUND(SUM(debit - credit), currency.decimal_places) != 0.0;
           ''', [tuple(self.ids)])

        # query_res = self._cr.fetchall()
        # if query_res:
        #     ids = [res[0] for res in query_res]
        #     sums = [res[1] for res in query_res]
        #     raise UserError(_("Cannot create unbalanced journal entry. Ids: %s\nDifferences debit - credit: %s") % (ids, sums))

class AccountMoveLine(models.Model):
    _inherit='account.move.line'

    def get_islr_retentions_dates(self):
        current_year = fields.Date.context_today(self).year
        # prueba = self.env['account.withholding.rate.table.line'].search([('percentage_amount_base','=',id)])
        if self.move_id.type in ['in_invoice','in_refund']:
            wh_rate_table_line = self.env['account.withholding.rate.table.line'].search([('concept', '=', self.product_id.service_concept_retention.id),
                                                                                         ('person_type', '=', self.move_id.partner_id.person_type)
                                                                                         ])
            # wh_rate_table_line = 'Prueba'
        elif self.move_id.type == 'out_invoice':
            wh_rate_table_line = self.env[('account.withholding.rate.table.line')].search([('concept', '=', self.product_id.service_concept_retention.id),
                                                                                           ('person_type', '=', 'PJD')
                                                                                           ])
        elif self.move_id.type == 'out_refund':
            wh_rate_table_line = self.env['account.withholding.rate.table.line'].search([('concept', '=', self.product_id.service_concept_retention.id),
                                                                                         ('person_type', '=', 'PJD')
                                                                                         ])
        return wh_rate_table_line

