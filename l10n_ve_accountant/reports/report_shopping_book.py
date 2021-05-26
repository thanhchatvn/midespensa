# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import time
from datetime import timedelta, datetime

from odoo import models, api, _
from odoo.exceptions import UserError


class ReportAccountHashIntegrity(models.AbstractModel):
    _name = 'report.l10n_ve_accountant.report_shooping_book'

    #falta ordenar el reporte por target_move y sortby
    def _get_account_move_entry(self, accounts, form_data, sortby, pass_date, display_account):
        cr = self.env.cr
        move_line = self.env['account.move.line']

        tables, where_clause, where_params = move_line._query_get()
        wheres = [""]
        if where_clause.strip():
            wheres.append(where_clause.strip())
        if form_data['target_move'] == 'posted':
            target_move = "AND m.state = 'posted'"
        else:
            target_move = ''
        sql = ('''
                SELECT l.id AS lid, acc.name as accname, l.account_id AS account_id, l.date AS ldate, j.code AS lcode, l.currency_id, 
                l.amount_currency, l.ref AS lref, l.name AS lname, COALESCE(l.debit,0) AS debit, COALESCE(l.credit,0) AS credit, 
                COALESCE(SUM(l.debit),0) - COALESCE(SUM(l.credit), 0) AS balance,
                m.name AS move_name, c.symbol AS currency_code, p.name AS partner_name
                FROM account_move_line l
                JOIN account_move m ON (l.move_id=m.id)
                LEFT JOIN res_currency c ON (l.currency_id=c.id)
                LEFT JOIN res_partner p ON (l.partner_id=p.id)
                JOIN account_journal j ON (l.journal_id=j.id)
                JOIN account_account acc ON (l.account_id = acc.id) 
                WHERE l.account_id IN %s AND l.journal_id IN %s ''' + target_move + ''' AND l.date = %s
                GROUP BY l.id, l.account_id, l.date,
                     j.code, l.currency_id, l.amount_currency, l.ref, l.name, m.name, c.symbol, p.name , acc.name
                     ORDER BY l.date DESC
        ''')
        params = (
            tuple(accounts.ids), tuple(form_data['journal_ids']), pass_date)
        cr.execute(sql, params)
        data = cr.dictfetchall()
        res = {}
        debit = credit = balance = 0.00
        for line in data:
            debit += line['debit']
            credit += line['credit']
            balance += line['balance']
        res['debit'] = debit
        res['credit'] = credit
        res['balance'] = balance
        res['lines'] = data
        return res

    @api.model
    def _get_report_values(self, docids, data=None):
        form_data = data['form']
        date_start = datetime.strptime(form_data['date_from'],
                                       '%Y-%m-%d').date()
        date_end = datetime.strptime(form_data['date_to'], '%Y-%m-%d').date()
        target_mov = ('posted',) if form_data['target_move'] =='posted' else ('draft','cancel','posted')
        currency_id = self.env['res.currency'].browse([form_data['currency_id'][0]])

        active_acc = data['form']['account_ids']
        accounts = self.env['account.account'].search(
            [('id', 'in', active_acc)]) if data['form']['account_ids'] else \
            self.env['account.account'].search([])
        print('hacker clara')
        print('hacker clara')
        print('hacker clara')
        print(accounts)

        if not data.get('form') or not self.env.context.get('active_model'):
            raise UserError(_("Form content is missing, this report cannot be printed."))

        sortby = data['form'].get('sortby')
        #las retenciones
        docs_ret = self.env['account.wh.iva'].search([('type', 'in', ('in_invoice', 'in_refund'))])
        #las facturas in_invoice y las facturas rectificativas in_refund
        docs_fac = self.env['account.move'].search([('type', 'in', ('in_refund', 'in_invoice')),
                                                    ('invoice_date','<=',date_end),
                                                    ('invoice_date','>=',date_start),
                                                    ('currency_id', '=', currency_id.id),
                                                    ('journal_id','in',form_data['journal_ids']),
                                                    ('state','in', target_mov)]).sorted(
            key=lambda r: r.journal_id.id and r.partner_id.name if sortby=='sort_journal_partner' else r.date).filtered(lambda x: x.line_ids.mapped('account_id') & accounts != self.env['account.account'])
        docs_fac_ajust = self.env['account.move'].search([('type', 'in', ('in_refund', 'in_invoice')),
                                                    ('ajust_date','<=',date_end),
                                                    ('ajust_date','>=',date_start),
                                                    ('transaction_type', '=', '04-ajuste'),
                                                    ('currency_id', '=', currency_id.id),
                                                    ('journal_id','in',form_data['journal_ids'])]).sorted(
            key=lambda r: r.journal_id.id and r.partner_id.name if sortby=='sort_journal_partner' else r.date).filtered(lambda x: x.line_ids.mapped('account_id') & accounts != self.env['account.account'])
        if not docs_fac:
            raise UserError('No se encontraron registros con estas características durante el periodo seleccionado. Verifique los datos ingresados')
        self.model = self.env.context.get('active_model')
        display_account = 'movement'
        codes = []
        if data['form'].get('journal_ids', False):
            codes = [journal.code for journal in
                     self.env['account.journal'].search(
                         [('id', 'in', data['form']['journal_ids'])])]
        days = date_end - date_start
        dates = []
        record = []
        for i in range(days.days + 1):
            dates.append(date_start + timedelta(days=i))
        for head in dates:
            pass_date = str(head)
            accounts_res = self.with_context(
                data['form'].get('used_context', {}))._get_account_move_entry(
                accounts, form_data, sortby,pass_date, display_account)
            if accounts_res['lines']:
                record.append({
                    'date': head,
                    'debit': accounts_res['debit'],
                    'credit': accounts_res['credit'],
                    'balance': accounts_res['balance'],
                    'child_lines': accounts_res['lines']
                })
        print('data')
        print(data)
        return {
            'doc_ids': docids,
            'doc_model': self.model,
            'data': data['form'],
            'docs': docs_ret,
            'fact': docs_fac,
            'docs_fac_ajust': docs_fac_ajust,
            'time': time,
            'Accounts': record,
            'print_journal': codes,
            'currency_id': currency_id,
        }
