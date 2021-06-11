# -*- coding: utf-8 -*-

import io
import base64
import xlsxwriter

from xlsxwriter.workbook import Workbook
from xlsxwriter.utility import xl_rowcol_to_cell
from datetime import timedelta, datetime, date

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class WizardShoppingBookXLSX(models.TransientModel):
    _inherit = "wizard.book"


    def prepare_header(self):
        header = [ 
            {'sequence': 1, 'name': 'Operación N°', 'larg': 10, 'col': {}},
            {'sequence': 2, 'name': 'Fecha\n de la \nFactura', 'larg': 10, 'col': {}},
            {'sequence': 3, 'name': 'RIF', 'larg': 15, 'col': {}},
            {'sequence': 4, 'name': 'Nombre \no \nRazón Social', 'larg': 30, 'col': {}},
            {'sequence': 5, 'name': 'Tipo \nde \nProveedor', 'larg': 10, 'col': {}},
            {'sequence': 6, 'name': 'Número \nde \nComprobante', 'larg': 15, 'col': {}},
            {'sequence': 7, 'name': 'Número \nde \nFactura', 'larg': 15, 'col': {}},
            {'sequence': 8, 'name': 'Número de \nControl de \nFactura', 'larg': 15, 'col': {}},
            {'sequence': 9, 'name': 'Número de \nNota de \nDébito', 'larg': 15, 'col': {}},
            {'sequence': 10, 'name': 'Número de \nNota de \nCrédito', 'larg': 15, 'col': {}},
            {'sequence': 11, 'name': 'Tipo \nde \nTransacción', 'larg': 10, 'col': {}},
            {'sequence': 12, 'name': 'Número \nde \nFactura \nAfectada', 'larg': 15, 'col': {}},
            {'sequence': 13, 'name': 'Total Compras \nIncluyendo el IVA', 'larg': 15, 'col': {}},
            {'sequence': 14, 'name': 'Compras sin Derecho \na Crédito IVA', 'larg': 15, 'col': {}},
            {'sequence': 15, 'name': 'Base \nImponible', 'larg': 15, 'col': {}},
            {'sequence': 16, 'name': '% \nAlícuota', 'larg': 15, 'col': {}},
            {'sequence': 17, 'name': 'Impuesto \nIVA', 'larg': 15, 'col': {}},
            {'sequence': 18, 'name': 'IVA Retenido \n(al vendedor)', 'larg': 15, 'col': {}},
            {'sequence': 19, 'name': 'IVA Retenido \n(a terceros)', 'larg': 15, 'col': {}},
            {'sequence': 20, 'name': 'Prorrata', 'larg': 15, 'col': {}},
        ]
        
        header_sort = sorted(header, key=lambda k: k['sequence'])
        return header_sort

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

    def get_data_shopping_book(self):
        self.ensure_one()
        data = {}
        data['form'] = \
            self.read(['date_from', 'date_to', 'journal_ids', 'target_move','display_account','account_ids','sortby','currency_id'])[0]
        
        form_data = data['form']
        date_start = form_data['date_from']
        date_end = form_data['date_to']
        target_mov = ('posted',) if form_data['target_move'] =='posted' else ('draft','cancel','posted')
        currency_id = self.env['res.currency'].browse([form_data['currency_id'][0]])

        active_acc = data['form']['account_ids']
        accounts = self.env['account.account'].search(
            [('id', 'in', active_acc)]) if data['form']['account_ids'] else \
            self.env['account.account'].search([])
        sortby = data['form'].get('sortby')
        docs_ret = self.env['account.wh.iva'].search([('type', 'in', ('in_invoice', 'in_refund'))])
        #invoices
        docs_fac = self.env['account.move'].search([('type', 'in', ('in_refund', 'in_invoice')),
                                                    ('invoice_date','<=',date_end),
                                                    ('invoice_date','>=',date_start),
                                                    ('currency_id', '=', currency_id.id),
                                                    ('journal_id','in',form_data['journal_ids']),
                                                    ('state','in', target_mov)]).sorted(
            key=lambda r: r.journal_id.id and r.partner_id.name if sortby=='sort_journal_partner' else r.date).filtered(lambda x: x.line_ids.mapped('account_id') & accounts != self.env['account.account'])
        #invoice refunds
        docs_fac_ajust = self.env['account.move'].search([('type', 'in', ('in_refund', 'in_invoice')),
                                                    ('ajust_date','<=',date_end),
                                                    ('ajust_date','>=',date_start),
                                                    ('transaction_type', '=', '04-ajuste'),
                                                    ('currency_id', '=', currency_id.id),
                                                    ('journal_id','in',form_data['journal_ids'])]).sorted(
            key=lambda r: r.journal_id.id and r.partner_id.name if sortby=='sort_journal_partner' else r.date).filtered(lambda x: x.line_ids.mapped('account_id') & accounts != self.env['account.account'])
        if not docs_fac:
            raise UserError(_('No results found.'))
        display_account = 'movement'
        days = date_end - date_start
        dates = []
        record = []
        for i in range(days.days + 1):
            dates.append(date_start + timedelta(days=i))
        for head in dates:
            pass_date = str(head)
            accounts_res = self._get_account_move_entry(
                accounts, form_data, sortby,pass_date, display_account)
            if accounts_res['lines']:
                record.append({
                    'date': head,
                    'debit': accounts_res['debit'],
                    'credit': accounts_res['credit'],
                    'balance': accounts_res['balance'],
                    'child_lines': accounts_res['lines']
                })
        
        return {
            'docs': docs_ret,
            'fact': docs_fac,
            'docs_fac_ajust': docs_fac_ajust,
            'Accounts': record,
            'currency_id': currency_id,
        }

    def print_xlsx(self):
        #Temp File
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output)
        
        #Format Cells
        num_format = self.env.user.company_id.currency_id.excel_format        
        bold = workbook.add_format({'bold': True})
        header_format = workbook.add_format({'bold': True, 'bg_color':'#BFBFBF', 'border': 1, 'top': 1, 'font_size': 8, 'align': 'center', 'valign': 'vcenter',   'font_name':'MS Sans Serif'})
        header_formatSM = workbook.add_format({'border': 1, 'bold': True, 'font_size': 18, 'align': 'center', 'valign': 'vcenter', 'font_name':'MS Sans Serif','italic': True})
        header_format_center = workbook.add_format({'bold': True, 'font_size': 10, 'align': 'center', 'valign': 'vcenter', 'font_name':'Arial'})
        header_formatBlue = workbook.add_format({'bold': True, 'font_size': 10, 'align': 'left', 'valign': 'vcenter', 'font_name':'Arial', 'font_color':'blue'})
        header_formatNB = workbook.add_format({'font_size': 10, 'align': 'left', 'valign': 'vcenter', 'font_name':'Arial'})
        header_formatSB = workbook.add_format({'bold': True, 'font_size': 10, 'align': 'center', 'valign': 'vcenter', 'font_name':'Arial', 'underline': True})
        middle = workbook.add_format({'bold': True, 'top': 1})
        left = workbook.add_format({'left': 1, 'top': 1, 'bold': True})
        right = workbook.add_format({'right': 1, 'top': 1})
        top = workbook.add_format({'top': 1})
        empty_format = workbook.add_format({'num_format': '0', 'bold': True, 'border': 1, 'top': 1, 'font_size': 8, 'align': 'center', 'valign': 'vcenter',   'font_name':'MS Sans Serif'})
        currency_format = workbook.add_format({'num_format': num_format, 'bold': True, 'border': 1, 'top': 1, 'font_size': 8, 'align': 'center', 'valign': 'vcenter',   'font_name':'MS Sans Serif'})
        currency_format2 = workbook.add_format({'num_format': num_format, 'bg_color':'#BFBFBF', 'bold': True, 'border': 1, 'top': 1, 'font_size': 8, 'align': 'center', 'valign': 'vcenter',   'font_name':'MS Sans Serif'})
        left_bg_format = workbook.add_format({'num_format': num_format, 'bg_color':'#BFBFBF', 'bold': True, 'border': 1, 'top': 1, 'font_size': 8, 'align': 'left', 'valign': 'vcenter',   'font_name':'MS Sans Serif'})
        formula_format = workbook.add_format({'num_format': num_format, 'bg_color':'#BFBFBF', 'bold': True, 'border': 1, 'top': 1, 'font_size': 8, 'align': 'center', 'valign': 'vcenter',  'font_name':'Arial'})
        formula_format1 = workbook.add_format ({'num_format': num_format, 'font_size': 10, 'align': 'center', 'valign': 'vcenter',  'font_name':'Arial'})
        formula_formatBorder = workbook.add_format ({'top': 1, 'num_format': num_format, 'font_size': 10, 'align': 'center', 'valign': 'vcenter',  'font_name':'Arial'})
        c_middle = workbook.add_format({'border': 1, 'bold': True, 'top': 1, 'num_format': num_format})
        report_format2 = workbook.add_format({'border': 1, 'bold': True, 'font_size': 8,  'font_name':'MS Sans Serif', 'align': 'center'})
        report_format = workbook.add_format({'border': 1, 'bold': True, 'font_size': 8,  'font_name':'MS Sans Serif'})
        rounding = self.env.user.company_id.currency_id.decimal_places or 2
        lang_code = self.env.user.lang or 'en_US'
        date_format = self.env['res.lang']._lang_get(lang_code).date_format
        time_format = self.env['res.lang']._lang_get(lang_code).time_format
        print_time = fields.Datetime.context_timestamp(self.with_context(tz=self.env.user.tz), fields.Datetime.now()).strftime(('%s %s') % (date_format, time_format)),
        
        def _get_data_float(data):
            if data is None or not data:
                return 0.0
            else:
                return self.env.user.company_id.currency_id.round(data) + 0.0
        
        def get_date_format(date):
            if date:
                # date = datetime.strptime(date, DEFAULT_SERVER_DATE_FORMAT)
                date = date.strftime(date_format)
            return date
        
        
        sheet_name = _('Shopping book')
        sheet = workbook.add_worksheet(sheet_name)
        view_context = self.env.context
        active_company = self.env.company
        allowed_companies = view_context.get('allowed_company_ids', False)
        
        journal_ids = self.journal_ids.mapped('code')
        journals_name = ', '.join(journal_ids)
        target_move = _('All Entries') if self.target_move == 'all' else _('All Posted Entries')
        sorted_by = _('Date') if self.sortby == 'sort_date' else _('Journal and Partner')
        period = _('%s to %s') %(get_date_format(self.date_from) or 'N/A', get_date_format(self.date_to) or 'N/A')
        
        logo = io.BytesIO(base64.b64decode(self.env.company.logo_web))
        sheet.merge_range('B1:D1','', report_format)
        sheet.merge_range('B2:D2','', report_format)
        sheet.merge_range('B3:D7','', report_format)
        sheet.merge_range('F1:L3','', header_formatSM)
        sheet.merge_range('B8:D8','', header_formatSM)
        sheet.merge_range('I8:L8','', header_formatSM)
        sheet.merge_range('B10:D10','', header_formatSM)
        sheet.merge_range('F10:G10','', header_formatSM)
        sheet.merge_range('I10:L10','', header_formatSM)
        sheet.merge_range('O11:Q11','', header_formatSM)
        sheet.write(0, 1, print_time[0], report_format)
        sheet.write(0, 5, sheet_name, header_formatSM)
        sheet.write(1, 1, _('Company: %s') % active_company.name, report_format)
        sheet.insert_image('B3', "company-logo.png", {'image_data': logo,'x_scale': 0.5, 'y_scale': 0.5})
        sheet.write(7, 1, _('Journals: %s') % journals_name, report_format)
        sheet.write(7, 8, _('Target Moves: %s') % target_move, report_format)
        sheet.write(9, 1, _('Sorted By: %s') % sorted_by, report_format)
        sheet.write(9, 5, _('Currency: %s') % self.currency_id.name, report_format)
        sheet.write(9, 8, _('Period: %s') % period, report_format)
        sheet.write(10, 14, _('COMPRAS INTERNAS O \nIMPORTACIONES'), header_format)
        
        
        #Data for report
        result = self.get_data_shopping_book()
        invoices = result['fact'].filtered(lambda inv: inv.transaction_type != '04-ajuste' and inv.state != 'annulled')
        invoice_refunds = result['docs_fac_ajust'].filtered(lambda inv: inv.state != 'annulled')
        
        for j, h in enumerate(self.prepare_header()):
            sheet.write(11, j, h['name'], header_format)
            sheet.set_column(11, j, h['larg'])
        count = 0
        row = 12
        col = 0
        R30 = sum(invoices.filtered(lambda inv: inv.type == 'in_invoice').invoice_line_ids.filtered(lambda whl: not whl.tax_ids).mapped('price_subtotal')) - sum(invoices.filtered(lambda inv: inv.type == 'in_refund').invoice_line_ids.filtered(lambda whl: not whl.tax_ids).mapped('price_subtotal'))
        R31 = 0
        R32 = 0
        R33 = 0
        R34 = 0
        R35 = 0
        R312 = 0
        R322 = 0
        R323 = 0
        R313 = 0
        R332 = 0
        R333 = 0
        R342 = 0
        R343 = 0
        pct_prorrata = 0
        total_price_subtotal = 0
        total_amount_tax = 0
        for inv in invoices:
            count += 1
            sheet.write(row, col, count, report_format2)
            col += 1
            sheet.write(row, col, inv.date, report_format2)
            col += 1
            sheet.write(row, col, inv.partner_id.vat or "-", report_format2)
            col += 1
            sheet.write(row, col, inv.partner_id.name, report_format2)
            col += 1
            sheet.write(row, col, inv.partner_id.residence_type or "-", report_format2)
            col += 1
            sheet.write(row, col, inv.name, report_format2)
            col += 1
            invoice_number = inv.vendor_invoice_number if inv.type == 'in_invoice' and not inv.debit_origin_id else '-'
            sheet.write(row, col, invoice_number, report_format2)
            col += 1
            sheet.write(row, col, inv.control_invoice_number, report_format2)
            col += 1
            vendor_invoice_number = inv.vendor_invoice_number if inv.debit_origin_id else '-'
            sheet.write(row, col, vendor_invoice_number, report_format2)
            col += 1
            vendor_invoice_number_refund = inv.vendor_invoice_number if inv.type == 'in_refund' else '-'
            sheet.write(row, col, vendor_invoice_number_refund, report_format2)
            col += 1
            sheet.write(row, col, inv.transaction_type, report_format2)
            col += 1
            reversed_entry = inv.reversed_entry_id.name if inv.type == 'in_refund' else '-'
            sheet.write(row, col, reversed_entry, report_format2)
            col += 1
            
            inv_amount_total = inv.amount_total * -1 if inv.type == 'in_refund' else inv.amount_total
            sheet.write(row, col, inv_amount_total, currency_format)
            # Formula
            start_range1 = xl_rowcol_to_cell(12, col)
            end_range1 = xl_rowcol_to_cell(len(invoices) + 12, col)
            fila_formula1 = xl_rowcol_to_cell(len(invoices) + 12 +1, col)
            formula1 = "=SUM({:s}:{:s})".format(start_range1, end_range1)
            sheet.write_formula(fila_formula1, formula1, formula_format, True) 
            # End Formula
            col += 1
            price_subtotal_untax = sum(inv.invoice_line_ids.filtered(lambda whl: not whl.tax_ids).mapped('price_subtotal'))
            untax_price_subtotal = price_subtotal_untax * -1 if inv.type == 'in_refund' else price_subtotal_untax
            sheet.write(row, col, untax_price_subtotal, currency_format)
            # Formula
            start_range1 = xl_rowcol_to_cell(12, col)
            end_range1 = xl_rowcol_to_cell(len(invoices) + 12, col)
            fila_formula1 = xl_rowcol_to_cell(len(invoices) + 12 +1, col)
            formula1 = "=SUM({:s}:{:s})".format(start_range1, end_range1)
            sheet.write_formula(fila_formula1, formula1, formula_format, True) 
            # End Formula
            col += 1
            price_subtotal_tax = sum(inv.invoice_line_ids.filtered(lambda whl: whl.tax_ids).mapped('price_subtotal'))
            tax_price_subtotal = price_subtotal_tax * -1 if inv.type == 'in_refund' else price_subtotal_tax
            total_price_subtotal += tax_price_subtotal
            sheet.write(row, col, tax_price_subtotal, currency_format)
            # Formula
            start_range1 = xl_rowcol_to_cell(12, col)
            end_range1 = xl_rowcol_to_cell(len(invoices) + 12, col)
            fila_formula1 = xl_rowcol_to_cell(len(invoices) + 12 +1, col)
            formula1 = "=SUM({:s}:{:s})".format(start_range1, end_range1)
            sheet.write_formula(fila_formula1, formula1, formula_format, True) 
            # End Formula
            col += 1
            if inv.type == 'in_invoice':
                total_amount_tax += inv.amount_tax
            if inv.type == 'in_refund':
                total_amount_tax -= inv.amount_tax
            tax_amount = sum(inv.invoice_line_ids.mapped('tax_ids.amount'))
            if tax_amount == 16:
                R33 += sum(inv.invoice_line_ids.filtered(lambda whl: whl.tax_ids).mapped('price_subtotal'))
                R34 += inv.amount_tax
            elif tax_amount > 16:
                R332 += sum(inv.invoice_line_ids.filtered(lambda whl: whl.tax_ids).mapped('price_subtotal'))
                R342 += inv.amount_tax
            else:
                R343 += inv.amount_tax
            
            if len(inv.invoice_line_ids.filtered(lambda line: len(line.mapped('tax_ids').filtered(lambda tax: tax.aliquot_type == 'reduced')))):
                R333 += sum(inv.invoice_line_ids.filtered(lambda line: len(line.mapped('tax_ids').filtered(lambda tax: tax.aliquot_type == 'reduced'))).mapped('price_subtotal'))
            
            
            
            aliquot = sum(inv.invoice_line_ids.mapped('tax_ids.amount'))
            sheet.write(row, col, str(aliquot) + ' %', report_format2)
            # Formula
            start_range1 = xl_rowcol_to_cell(12, col)
            end_range1 = xl_rowcol_to_cell(len(invoices) + 12, col)
            fila_formula1 = xl_rowcol_to_cell(len(invoices) + 12 +1, col)
            formula1 = "=SUM({:s}:{:s})".format(start_range1, end_range1)
            sheet.write_formula(fila_formula1, formula1, formula_format, True) 
            # End Formula
            
            col += 1
            amount_tax = inv.amount_tax * -1 if inv.type == 'in_refund' else inv.amount_tax
            sheet.write(row, col, amount_tax, currency_format)
            # Formula
            start_range1 = xl_rowcol_to_cell(12, col)
            end_range1 = xl_rowcol_to_cell(len(invoices) + 12, col)
            fila_formula1 = xl_rowcol_to_cell(len(invoices) + 12 +1, col)
            formula1 = "=SUM({:s}:{:s})".format(start_range1, end_range1)
            sheet.write_formula(fila_formula1, formula1, formula_format, True) 
            # End Formula
            col += 1
            inv_amount_wh_iva = inv.amount_wh_iva - sum(inv.wh_id.wh_lines.filtered(lambda whl: whl.payments_three).mapped('ret_amount'))
            amount_wh_iva = inv_amount_wh_iva * -1 if inv.type == 'in_refund' else inv_amount_wh_iva
            sheet.write(row, col, amount_wh_iva, currency_format)
            # Formula
            start_range1 = xl_rowcol_to_cell(12, col)
            end_range1 = xl_rowcol_to_cell(len(invoices) + 12, col)
            fila_formula1 = xl_rowcol_to_cell(len(invoices) + 12 +1, col)
            formula1 = "=SUM({:s}:{:s})".format(start_range1, end_range1)
            sheet.write_formula(fila_formula1, formula1, formula_format, True) 
            # End Formula
            col += 1
            
            wh_inv_ret_amount = sum(inv.wh_id.wh_lines.filtered(lambda whl: whl.payments_three).mapped('ret_amount'))
            wh_ret_amount = wh_inv_ret_amount * -1 if inv.type == 'in_refund' else wh_inv_ret_amount
            sheet.write(row, col, wh_ret_amount, currency_format)
            # Formula
            start_range1 = xl_rowcol_to_cell(12, col)
            end_range1 = xl_rowcol_to_cell(len(invoices) + 12, col)
            fila_formula1 = xl_rowcol_to_cell(len(invoices) + 12 +1, col)
            formula1 = "=SUM({:s}:{:s})".format(start_range1, end_range1)
            sheet.write_formula(fila_formula1, formula1, formula_format, True) 
            # End Formula
            col += 1
            
            if sum(inv.invoice_line_ids.filtered(lambda whl: sum(whl.tax_ids.mapped('amount')) > 0).mapped('price_subtotal')):
                pct_prorrata = sum(inv.invoice_line_ids.filtered(lambda whl: sum(whl.tax_ids.mapped('amount')) == 0 and whl.tax_ids).mapped('price_subtotal')) / sum(inv.invoice_line_ids.filtered(lambda whl: sum(whl.tax_ids.mapped('amount')) > 0).mapped('price_subtotal'))
            prorrata = pct_prorrata * inv.amount_tax
            prorrata_amount = prorrata * -1 if inv.type == 'in_refund' else prorrata
            sheet.write(row, col, prorrata_amount, currency_format)
            # Formula
            start_range1 = xl_rowcol_to_cell(12, col)
            end_range1 = xl_rowcol_to_cell(len(invoices) + 12, col)
            fila_formula1 = xl_rowcol_to_cell(len(invoices) + 12 +1, col)
            formula1 = "=SUM({:s}:{:s})".format(start_range1, end_range1)
            sheet.write_formula(fila_formula1, formula1, formula_format, True) 
            # End Formula
            col += 1
            
            col  = 0
            row += 1
        
        # Second Table
        m1 = xl_rowcol_to_cell(len(invoices) + 15, 13)
        m2 = xl_rowcol_to_cell(len(invoices) + 15, 15)
        sheet.merge_range('{:s}:{:s}'.format(m1, m2),'', header_format)
        
        row2 = len(invoices) + 15
        col2 = 16
        sheet.write(row2, col2, '', header_format)
        col2 += 1
        sheet.write(row2, col2, 'Base imponible', header_format)
        col2 += 1
        sheet.write(row2, col2, '', header_format)
        col2 += 1
        sheet.write(row2, col2, 'Crédito fiscal', header_format)
        
        col2 = 13
        row2 += 1
        m1 = xl_rowcol_to_cell(row2, col2)
        m2 = xl_rowcol_to_cell(row2, col2+2)
        sheet.merge_range('{:s}:{:s}'.format(m1, m2),'', report_format)
        sheet.write(row2, col2, 'Total : Compras Exentas y/o sin derecho a crédito fiscal', report_format)
        col2 += 3
        sheet.write(row2, col2, '30', report_format2)
        col2 += 1
        sheet.write(row2, col2, R30, currency_format)
        col2 += 1
        sheet.write(row2, col2, '', report_format2)
        col2 += 1
        sheet.write(row2, col2, '', currency_format)
        
        col2 = 13
        row2 += 1
        m1 = xl_rowcol_to_cell(row2, col2)
        m2 = xl_rowcol_to_cell(row2, col2+2)
        sheet.merge_range('{:s}:{:s}'.format(m1, m2),'', report_format)
        sheet.write(row2, col2, 'Compras Importación afectadas solo Alícuota General', report_format)
        col2 += 3
        sheet.write(row2, col2, '31', report_format2)
        col2 += 1
        sheet.write(row2, col2, R31, currency_format)
        col2 += 1
        sheet.write(row2, col2, '32', report_format2)
        col2 += 1
        sheet.write(row2, col2, R32, currency_format)
        
        col2 = 13
        row2 += 1
        m1 = xl_rowcol_to_cell(row2, col2)
        m2 = xl_rowcol_to_cell(row2, col2+2)
        sheet.merge_range('{:s}:{:s}'.format(m1, m2),'', report_format2)
        sheet.write(row2, col2, 'Compras Importación Afectas en Alícuota General + Adicional', report_format)
        col2 += 3
        sheet.write(row2, col2, '312', report_format2)
        col2 += 1
        sheet.write(row2, col2, R312, currency_format)
        col2 += 1
        sheet.write(row2, col2, '322', report_format2)
        col2 += 1
        sheet.write(row2, col2, R322, currency_format)
        
        col2 = 13
        row2 += 1
        m1 = xl_rowcol_to_cell(row2, col2)
        m2 = xl_rowcol_to_cell(row2, col2+2)
        sheet.merge_range('{:s}:{:s}'.format(m1, m2),'', report_format)
        sheet.write(row2, col2, 'Compras Importación Afectas en Alícuota Reducida', report_format)
        col2 += 3
        sheet.write(row2, col2, '313', report_format2)
        col2 += 1
        sheet.write(row2, col2, R313, currency_format)
        col2 += 1
        sheet.write(row2, col2, '323', report_format2)
        col2 += 1
        sheet.write(row2, col2, R323, currency_format)
        
        col2 = 13
        row2 += 1
        m1 = xl_rowcol_to_cell(row2, col2)
        m2 = xl_rowcol_to_cell(row2, col2+2)
        sheet.merge_range('{:s}:{:s}'.format(m1, m2),'', report_format)
        sheet.write(row2, col2, 'Compras Internas Afectas en Alícuota General + Adicional', report_format)
        col2 += 3
        sheet.write(row2, col2, '332', report_format2)
        col2 += 1
        sheet.write(row2, col2, R332, currency_format)
        col2 += 1
        sheet.write(row2, col2, '342', report_format2)
        col2 += 1
        sheet.write(row2, col2, R342, currency_format)
        
        col2 = 13
        row2 += 1
        m1 = xl_rowcol_to_cell(row2, col2)
        m2 = xl_rowcol_to_cell(row2, col2+2)
        sheet.merge_range('{:s}:{:s}'.format(m1, m2),'', report_format)
        sheet.write(row2, col2, 'Compras Internas Afectas en Alícuota Reducida', report_format)
        col2 += 3
        sheet.write(row2, col2, '333', report_format2)
        col2 += 1
        sheet.write(row2, col2, R333, currency_format)
        col2 += 1
        sheet.write(row2, col2, '343', report_format2)
        col2 += 1
        sheet.write(row2, col2, R343, currency_format)
        
        col2 = 13
        row2 += 1
        m1 = xl_rowcol_to_cell(row2, col2)
        m2 = xl_rowcol_to_cell(row2, col2+2)
        sheet.merge_range('{:s}:{:s}'.format(m1, m2),'', report_format)
        sheet.write(row2, col2, 'Compras Internas Afectas solo Alícuota General', report_format)
        col2 += 3
        sheet.write(row2, col2, '33', report_format2)
        col2 += 1
        R33 = total_price_subtotal
        sheet.write(row2, col2, R33, currency_format)
        col2 += 1
        sheet.write(row2, col2, '34', report_format2)
        col2 += 1
        R34 = total_amount_tax
        sheet.write(row2, col2, R34, currency_format)
        
        col2 = 13
        row2 += 1
        m1 = xl_rowcol_to_cell(row2, col2)
        m2 = xl_rowcol_to_cell(row2, col2+2)
        sheet.merge_range('{:s}:{:s}'.format(m1, m2),'', report_format)
        sheet.write(row2, col2, 'Total', header_format)
        col2 += 3
        sheet.write(row2, col2, '35', currency_format2)
        col2 += 1
        t_R35 = R30+R332+R333+R33+R312+R313
        sheet.write(row2, col2, t_R35, currency_format2)
        col2 += 1
        sheet.write(row2, col2, '36', currency_format2)
        col2 += 1
        t_R36 = R34+R342+R343+R32+R322+R323
        sheet.write(row2, col2, t_R36, currency_format2)
        
        row3_head = row2 + 4
        row3 = row2 + 4
        if invoice_refunds:
            col3 = 0
            m1 = xl_rowcol_to_cell(row3-1, 14)
            m2 = xl_rowcol_to_cell(row3-1, 16)
            sheet.merge_range('{:s}:{:s}'.format(m1, m2),'', header_format)
            sheet.write(row3 -1, 14, 'COMPRAS INTERNAS O \nIMPORTACIONES', header_format)
            
            for j, h in enumerate(self.prepare_header()):
                sheet.write(row3, j, h['name'], header_format)
            
            R33 = 0
            R34 = 0
            R332 = 0
            R333 = 0
            R342 = 0
            R343 = 0
            pct_prorrata_ref = 0
            total_amount_tax_a = 0
            
            countr = 0
            row3 += 1
            for inv in invoice_refunds:
                countr += 1
                nro = 'A%s' %countr
                sheet.write(row3, col3, nro, report_format2)
                col3 += 1
                
                sheet.write(row3, col3, inv.date, report_format2)
                col3 += 1
                sheet.write(row3, col3, inv.partner_id.vat or "-", report_format2)
                col3 += 1
                sheet.write(row3, col3, inv.partner_id.name, report_format2)
                col3 += 1
                sheet.write(row3, col3, inv.partner_id.residence_type or "-", report_format2)
                col3 += 1
                sheet.write(row3, col3, inv.name, report_format2)
                col3 += 1
                sheet.write(row3, col3, inv.vendor_invoice_number, report_format2)
                col3 += 1
                sheet.write(row3, col3, inv.control_invoice_number, report_format2)
                col3 += 1
                sheet.write(row3, col3, '', report_format2)
                col3 += 1
                sheet.write(row3, col3, '', report_format2)
                col3 += 1
                sheet.write(row3, col3, inv.transaction_type, report_format2)
                col3 += 1
                sheet.write(row3, col3, '', report_format2)
                col3 += 1
                # ~ sheet.write(row3, col3, inv.amount_total, currency_format)
                # ~ col += 1
                
                
                sheet.write(row3, col3, inv.amount_total, currency_format)
                # Formula
                start_range1 = xl_rowcol_to_cell(row3_head, col3)
                end_range1 = xl_rowcol_to_cell(len(invoice_refunds) + row3_head, col3)
                fila_formula1 = xl_rowcol_to_cell(len(invoice_refunds) + row3_head +1, col3)
                formula1 = "=SUM({:s}:{:s})".format(start_range1, end_range1)
                sheet.write_formula(fila_formula1, formula1, formula_format, True) 
                # End Formula
                
                
                col3 += 1
                ref_price_subtotal = sum(inv.invoice_line_ids.filtered(lambda whl: not whl.tax_ids).mapped('price_subtotal'))
                sheet.write(row3, col3, ref_price_subtotal, currency_format)
                # Formula
                start_range1 = xl_rowcol_to_cell(row3_head, col3)
                end_range1 = xl_rowcol_to_cell(len(invoice_refunds) + row3_head, col3)
                fila_formula1 = xl_rowcol_to_cell(len(invoice_refunds) + row3_head +1, col3)
                formula1 = "=SUM({:s}:{:s})".format(start_range1, end_range1)
                sheet.write_formula(fila_formula1, formula1, formula_format, True) 
                # End Formula
                col3 += 1
                ref_price_subtotal_tax = sum(inv.invoice_line_ids.filtered(lambda whl: whl.tax_ids).mapped('price_subtotal'))
                sheet.write(row3, col3, ref_price_subtotal_tax, currency_format)
                # Formula
                start_range1 = xl_rowcol_to_cell(row3_head, col3)
                end_range1 = xl_rowcol_to_cell(len(invoice_refunds) + row3_head, col3)
                fila_formula1 = xl_rowcol_to_cell(len(invoice_refunds) + row3_head +1, col3)
                formula1 = "=SUM({:s}:{:s})".format(start_range1, end_range1)
                sheet.write_formula(fila_formula1, formula1, formula_format, True) 
                # End Formula
                col3 += 1
                ref_aliquot = sum(inv.invoice_line_ids.mapped('tax_ids.amount'))
                sheet.write(row3, col3,  str(ref_aliquot) + ' %', report_format2)
                # Formula
                start_range1 = xl_rowcol_to_cell(row3_head, col3)
                end_range1 = xl_rowcol_to_cell(len(invoice_refunds) + row3_head, col3)
                fila_formula1 = xl_rowcol_to_cell(len(invoice_refunds) + row3_head +1, col3)
                formula1 = "=SUM({:s}:{:s})".format(start_range1, end_range1)
                sheet.write_formula(fila_formula1, formula1, formula_format, True) 
                # End Formula
                col3 += 1
                sheet.write(row3, col3,  inv.amount_tax, currency_format)
                # Formula
                start_range1 = xl_rowcol_to_cell(row3_head, col3)
                end_range1 = xl_rowcol_to_cell(len(invoice_refunds) + row3_head, col3)
                fila_formula1 = xl_rowcol_to_cell(len(invoice_refunds) + row3_head +1, col3)
                formula1 = "=SUM({:s}:{:s})".format(start_range1, end_range1)
                sheet.write_formula(fila_formula1, formula1, formula_format, True) 
                # End Formula
                
                if sum(inv.invoice_line_ids.mapped('tax_ids.amount')) == 16:
                    R33 += sum(inv.invoice_line_ids.filtered(lambda whl: whl.tax_ids).mapped('price_subtotal'))
                    R34 += inv.amount_tax
                elif sum(inv.invoice_line_ids.mapped('tax_ids.amount')) > 16:
                    R332 += sum(inv.invoice_line_ids.filtered(lambda whl: whl.tax_ids).mapped('price_subtotal'))
                    R342 += inv.amount_tax
                else:
                    R333 += sum(inv.invoice_line_ids.filtered(lambda whl: whl.tax_ids).mapped('price_subtotal'))
                    R343 += inv.amount_tax
                
                total_amount_tax_a += inv.amount_tax
                
                
                col3 += 1
                inv_amount_wh_iva = inv.amount_wh_iva - sum(inv.wh_id.wh_lines.filtered(lambda whl: whl.payments_three).mapped('ret_amount'))
                amount_wh_iva = inv_amount_wh_iva * -1 if inv.type == 'in_refund' else inv_amount_wh_iva
                sheet.write(row3, col3, amount_wh_iva, currency_format)
                # Formula
                start_range1 = xl_rowcol_to_cell(row3_head, col3)
                end_range1 = xl_rowcol_to_cell(len(invoice_refunds) + row3_head, col3)
                fila_formula1 = xl_rowcol_to_cell(len(invoice_refunds) + row3_head +1, col3)
                formula1 = "=SUM({:s}:{:s})".format(start_range1, end_range1)
                sheet.write_formula(fila_formula1, formula1, formula_format, True) 
                # End Formula
                col3 += 1
                wh_id_amount = sum(inv.wh_id.wh_lines.filtered(lambda whl: whl.payments_three).mapped('ret_amount'))
                wh_id_amount_inv = wh_id_amount * -1 if inv.type == 'in_refund' else wh_id_amount
                sheet.write(row3, col3, wh_id_amount_inv, currency_format)
                # Formula
                start_range1 = xl_rowcol_to_cell(row3_head, col3)
                end_range1 = xl_rowcol_to_cell(len(invoice_refunds) + row3_head, col3)
                fila_formula1 = xl_rowcol_to_cell(len(invoice_refunds) + row3_head +1, col3)
                formula1 = "=SUM({:s}:{:s})".format(start_range1, end_range1)
                sheet.write_formula(fila_formula1, formula1, formula_format, True) 
                # End Formula
                
                col3 += 1
                if sum(inv.invoice_line_ids.filtered(lambda whl: sum(whl.tax_ids.mapped('amount')) > 0).mapped('price_subtotal')):
                    pct_prorrata_ref = sum(inv.invoice_line_ids.filtered(lambda whl: sum(whl.tax_ids.mapped('amount')) == 0 and whl.tax_ids).mapped('price_subtotal')) / sum(inv.invoice_line_ids.filtered(lambda whl: sum(whl.tax_ids.mapped('amount')) > 0).mapped('price_subtotal'))
                prorrata_ref = pct_prorrata_ref * inv.amount_tax
                prorrata_amount_ref = prorrata_ref * -1 if inv.type == 'in_refund' else prorrata_ref
                sheet.write(row3, col3, prorrata_amount_ref, currency_format)
                # Formula
                start_range1 = xl_rowcol_to_cell(row3_head, col3)
                end_range1 = xl_rowcol_to_cell(len(invoice_refunds) + row3_head, col3)
                fila_formula1 = xl_rowcol_to_cell(len(invoice_refunds) + row3_head +1, col3)
                formula1 = "=SUM({:s}:{:s})".format(start_range1, end_range1)
                sheet.write_formula(fila_formula1, formula1, formula_format, True) 
                # End Formula
                
                
                col3  = 0
                row3 += 1
            
            row4 = row3 + 2
            col4 = 13
            
            # Second Table Refund invoice
            m1 = xl_rowcol_to_cell(row4, 13)
            m2 = xl_rowcol_to_cell(row4, 14)
            sheet.merge_range('{:s}:{:s}'.format(m1, m2),'', header_format)
            sheet.write(row4, col4, 'Saldo anterior de Ajuste', left_bg_format)
            col4 += 2
            sheet.write(row4, col4, 0, currency_format)
            col4 += 1
            sheet.write(row4, col4, 0, currency_format)
            
            row4 += 1
            col4 = 13
            
            m1 = xl_rowcol_to_cell(row4, 13)
            m2 = xl_rowcol_to_cell(row4, 14)
            sheet.merge_range('{:s}:{:s}'.format(m1, m2),'', header_format)
            sheet.write(row4, col4, 'Ajustes de este periodo', left_bg_format)
            col4 += 2
            sheet.write(row4, col4, total_amount_tax_a, currency_format)
            col4 += 1
            sheet.write(row4, col4, 0, currency_format)
            
            row4 += 1
            col4 = 13
            
            m1 = xl_rowcol_to_cell(row4, 13)
            m2 = xl_rowcol_to_cell(row4, 14)
            sheet.merge_range('{:s}:{:s}'.format(m1, m2),'', header_format)
            sheet.write(row4, col4, 'Total Ajuste Aplicable', left_bg_format)
            col4 += 2
            sheet.write(row4, col4, 0, currency_format)
            col4 += 1
            sheet.write(row4, col4, 0, currency_format)
            
            row4 += 1
            col4 = 13
            
            m1 = xl_rowcol_to_cell(row4, 13)
            m2 = xl_rowcol_to_cell(row4, 14)
            sheet.merge_range('{:s}:{:s}'.format(m1, m2),'', header_format)
            sheet.write(row4, col4, 'Ajuste Aplicado', left_bg_format)
            col4 += 2
            sheet.write(row4, col4, 0, currency_format)
            col4 += 1
            sheet.write(row4, col4, 0, currency_format)
            
            row4 += 2
            col4 = 13
            
            m1 = xl_rowcol_to_cell(row4, 13)
            m2 = xl_rowcol_to_cell(row4, 14)
            sheet.merge_range('{:s}:{:s}'.format(m1, m2),'', header_format)
            sheet.write(row4, col4, 'Saldo de Ajuste próximo periodo', left_bg_format)
            col4 += 2
            sheet.write(row4, col4, 0, currency_format)
            col4 += 1
            sheet.write(row4, col4, 0, currency_format)
        
        sheet.set_row(10, 30, )
        sheet.set_row(11, 50, )
        sheet.set_row(row3_head-1, 30, )
        sheet.set_row(row3_head, 50, )
        workbook.close()
        xlsx_data = output.getvalue()
        fname = '%s %s-%s' %(sheet_name, get_date_format(self.date_from), get_date_format(self.date_to))
        export_id = self.env['book.export.excel'].create({ 'excel_file': base64.encodestring(xlsx_data),'file_name': fname + '.xlsx'})
        view = self.env.ref('l10n_ve_accountant.view_book_export_excel')
        return {
            'name': _('Download Excel %s') %sheet_name,
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'book.export.excel',
            'views': [(view.id, 'form')],
            'view_id': view.id,
            'target': 'new',
            'res_id': export_id.id,
            'context': self.env.context,
        }
        
