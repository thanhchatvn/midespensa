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
# ~ from imp import reload
# ~ import sys
# ~ reload(sys)
# ~ sys.setdefaultencoding('utf8')

from datetime import timedelta
import collections
import base64

from odoo import api, fields, models, tools, _
from odoo import models, fields, api, exceptions, _
from odoo.addons import decimal_precision as dp
from odoo.tools import float_compare, float_is_zero
from odoo.exceptions import UserError, RedirectWarning, ValidationError
import calendar

TYPE2JOURNAL = {
    'out_invoice': 'sale',
    'in_invoice': 'purchase',
    'out_refund': 'sale',
    'in_refund': 'purchase',
}


class AccountWhIva(models.Model):
    _name = "account.wh.iva"
    _inherit = ['mail.thread']
    _description = "Withholding Vat"
    _rec_name = "number"
    _order = 'create_date desc, id desc'
    
    def name_get(self):
        result = []
        for wh in self:
            result.append((wh.id, "%s" % (wh.number or wh.customer_doc_number or str(wh.partner_id.name)+', '+str(wh.id) or '')))
        return result

    def action_cancel_draft(self):
        for wh in self:
            for whl in wh.wh_lines:
                if whl.state=='withold':
                    raise UserError(_('No se puede cancelar una retención IVA con una factura declarada.'))
                    return
            wh.state='cancel'
            wh.wh_lines = False
            for whl in wh.wh_lines:
                whl.invoice_id.wh_id = False

    def action_draft(self):
        for wh in self:
            wh.state = 'draft';
    
    def action_confirm(self):
        for hw in self:
            if hw.wh_lines:
                # for hwl in hw.wh_lines:
                #     if  hwl.ret_amount <= 0:
                #         raise UserError(_('La retención del IVA de cada factura debe ser mayor a 0..'))
                #         return
                for hwl in hw.wh_lines:
                    if hwl.state=='draft':
                        hwl.write({'state': 'confirmed'})
            else:
                raise UserError(_('No se puede confirmar una retención sin asociar facturas.'))
                return
        return self.write({'state': 'confirmed',
                    'number': self.env['ir.sequence'].next_by_code('account.wh.iva.in_invoice') if self.type in ('in_invoice', 'in_refund') and not self.number else self.number or ''})
    
    def action_withhold(self):
        for hw in self:
            if hw.wh_lines:
                for hwl in hw.wh_lines:
                    if hwl.state=='confirmed':
                        hwl.invoice_id.action_post()
        return self.write({'state': 'withhold'})
    
    def action_declaration(self):
        for hw in self:
            for hwl in hw.wh_lines:
                if hwl.state=='confirmed':
                    hwl.invoice_id.action_post()
        return self.write({'state': 'withhold'})

    @api.constrains('wh_lines')
    def _check_wh_lines(self):
        wh_list = []
        list_line = []
        #~ if not self.wh_lines:
            #~ raise ValidationError(_('Un comprobante de retención debe tener facturas asociadas.'))
        for wh in self:
            for line in wh.wh_lines:
                wh_list.append(line.invoice_id.id)
        invoice_ids = self.env['account.move'].search(
            [
                ('partner_id', '=', self.partner_id.id),
                ('state', '=', 'draft'),
                ('type', '=', self.type),
                ('wh_id', '=', False),
            ]
        )
        tax_list = []
        listy = []
        # if invoice_ids:
        #     for inv in invoice_ids:
        #         for tax in inv.tax_line_ids:
        #             if tax.tax_id.amount > 0:
        #                 tax_list.append(self.env['account.move.line'].search(
        #                     [
        #                         ('invoice_id', '=', inv.id),
        #                         ('tax_id', '!=', tax.tax_id.id),
        #                         ('amount', '>', 0),
        #                     ]
        #                 ).invoice_id.id)
        #             for wh in self.wh_lines:
        #                 if wh.invoice_id.id == tax.invoice_id.id and wh.ret_tax.id == tax.tax_id.id:
        #                     listy.append(wh.invoice_id.id)
        #         tax_list_filter = filter(lambda i: i is not False, tax_list)
        #         wh_list_filter = filter(lambda i: i in tax_list_filter, wh_list)
        #         counter_tax = collections.Counter(tax_list_filter)
        #         counter_wh = collections.Counter(wh_list_filter)
        #         for k in counter_wh.values():
        #             if k not in counter_tax.values():
        #                 raise UserError(_('La Factura %s tiene mas de un impuesto direferente. No debe generar comprobante para un solo impuesto de la factura.') % inv.name_get())

    def search_tax_whlines(self):
        wh_list = []
        list_line = []
        taxes_ids = []
        tax_list = []
        tax_list = []
        invoice_ids = []
        #~ if not self.wh_lines:
            #~ raise ValidationError(_('Un comprobante de retención debe tener facturas asociadas.'))
        for wh in self:
            for line in wh.wh_lines:
                wh_list.append(line.invoice_id.id)
            invoice_ids = self.env['account.move'].search(
                [
                    ('partner_id', '=', wh.partner_id.id),
                    ('state', '=', 'draft'),
                    ('type', '=', wh.type),
                ]
            )
        # ~ if invoice_ids:
            # ~ for inv in invoice_ids:
                # ~ for tax in inv.tax_line_ids:
                    # ~ if tax.amount:
                        # ~ if tax.tax_id.amount > 0:
                            # ~ tax_list.append(self.env['account.invoice.tax'].search(
                                # ~ [
                                    # ~ ('invoice_id', '=', inv.id),
                                    # ~ ('tax_id', '!=', tax.tax_id.id),
                                    # ~ ('amount', '>', 0),
                                # ~ ]
                            # ~ ).invoice_id.id)
            # ~ tax_list_filter = filter(lambda i: i is not False, tax_list)
            # ~ wh_list_filter = filter(lambda i: i in tax_list_filter, wh_list)
            # ~ counter_tax = collections.Counter(tax_list_filter)
            # ~ counter_wh = collections.Counter(wh_list_filter)
            # ~ for k in counter_wh.values():
                # ~ if k not in counter_tax.values():
                    # ~ raise UserError(_('La Factura tiene mas de un impuesto direferente. No debe generar comprobante para un solo impuesto de la factura.')
                                    # ~ )
                # ~ return True

    @api.model
    def _default_journal(self):
        if self._context.get('default_journal_id', False):
            return self.env['account.journal'].browse(self._context.get('default_journal_id'))
        inv_type = self._context.get('type', 'out_invoice')
        inv_types = inv_type if isinstance(inv_type, list) else [inv_type]
        company_id = self._context.get('company_id', self.env.user.company_id.id)
        domain = [('company_id', '=', company_id)]
        return self.env['account.journal'].search(domain, limit=1)

    @api.depends('wh_lines.ret_amount','wh_lines.state','wh_lines')
    def _get_amount_total(self):
        for wh in self:
            wh.total_tax_ret = round(sum(wh.wh_lines.filtered(lambda whl: whl.state != 'annulled').mapped('ret_amount')), 2)
            
    @api.onchange('partner_id')
    def onchange_partner_id(self):
        vals = []
        domain = {}
        warning = {}
        if self.partner_id:
            inv_ids = []
            for wh in self:
                invoice_ids = self.env['account.move'].search(
                    [
                        ('partner_id', '=', wh.partner_id.id),
                        ('state', '=', 'draft'),
                        ('type', '=', wh.type),
                        ('wh_id', '=', False),
                        
                    ],
                limit=1)
                if not invoice_ids:
                    self.partner_id = False
                    self.wh_lines = False
                    warning = {
                        'title': _('Aviso!'),
                        'message': _('Este proveedor no tiene facturas para generar retención.'),
                    }
                    return {'warning': warning}
                else:
                    for inv in invoice_ids:
                        amount_retention = 100.0 if inv.retention == '03-ordinary' else 75.0 if inv.retention == '02-special' else 0
                        type_tax_use = 'purchase'
                        if inv.type in ('out_invoice', 'out_refund', 'out_receipt'):
                            type_tax_use = 'sale'
                        for group in inv.amount_by_group:
                            tax = self.env['account.tax'].search([
                                ('tax_group_id', '=', group[6]),
                                ('company_id', '=', inv.company_id.id),
                                ('type_tax_use', '=', type_tax_use),
                            ])
                            amount_tax = group[1]
                            invoice_line = inv.line_ids.filtered(lambda line: line.tax_line_id.id == tax.id)
                            inv_ids.append((0, False, {
                                    'invoice_id': inv.id,
                                    'base_tax': group[2],
                                    'rate_amount': float(amount_retention),
                                    'ret_tax': tax.id,
                                    'amount_tax': amount_tax,
                                    'ret_amount': (amount_retention * amount_tax) / 100,
                                    'payments_three': invoice_line.payments_three or False
                                }
                            ))
                    vals = {'wh_lines': inv_ids}
                    return {'value': vals}
    
    @api.onchange('partner_id')
    @api.model
    def _get_default_witholding_account(self):
        for wh in self:
            if wh.type == 'out_invoice' or wh.type == 'out_refund':
                wh.account_id = wh.company_id.sale_iva_ret_account.id
            else:
                wh.account_id = wh.company_id.purchase_iva_ret_account.id

    def act_getfile(self, wh_id, tax_period):
        wh_iva_obj = self.env['account.wh.iva']
        zero = 0
        type_doc = ''
        content = ''
        if not wh_id:
            raise UserError(("El RIF para la compañía no ha sido establecido o el registro se encuentra vacio, "
                             "verifique nuevamente."))
        for wh in wh_id:
            if not wh.company_id.vat:
                raise UserError('El RIF para la compañía %s no ha sido establecido.' % wh.company_id.name)
            if not wh.partner_id.vat:
                raise UserError('El RIF para el Proveedor %s no ha sido establecido.' % wh.partner_id.name)

            type = 'C' if wh.type in ('in_invoice', 'in_refund') else 'V'

            if wh.type == 'in_invoice':
                type_doc = '01'
            if wh.type == 'out_invoice':
                type_doc = '02'
            if wh.type == 'in_refund':
                type_doc = '03'
            for whl in wh.wh_lines:
                if whl.state != 'annulled' and whl.ret_tax.amount > 0:
                    if whl.invoice_id.vendor_invoice_number and whl.invoice_id.control_invoice_number:
                        pass
                    else:
                        raise UserError('El Nro factura o Nro de Control de la factura %s no se encuentra establecido, verifique nuevamente'
                                        % whl.invoice_id.name)
                    content += '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%.2f\t%.2f\t%.2f\t%s\t%s\t%.2f\t%.2f\t%s\n' % (
                        wh.company_id.vat.replace('-', ''),
                        tax_period,
                        wh.date,
                        type,
                        type_doc,
                        wh.partner_id.vat.replace('-', ''),
                        whl.invoice_id.vendor_invoice_number,
                        whl.invoice_id.control_invoice_number,
                        -whl.invoice_id.amount_total if whl.invoice_id.type == 'in_refund' else whl.invoice_id.amount_total,
                        -whl.base_tax if whl.invoice_id.type == 'in_refund' else whl.base_tax,
                        -whl.ret_amount if whl.invoice_id.type == 'in_refund' else whl.ret_amount,
                        zero if not whl.invoice_id.invoice_origin else whl.invoice_id.invoice_origin,
                        wh.number,
                        -whl.invoice_id.exempt_amount if whl.invoice_id.type == 'in_refund' else whl.invoice_id.exempt_amount,
                        whl.ret_tax.amount,
                        zero)
        return base64.encodebytes(bytes(content, 'utf-8'))

    def download_txt(self):
        name = '%s.txt' %(self.number)
        today = fields.Date.today().split('-')
        tax_period = today[0]+today[1] if not self.period else self.period
        content = self.act_getfile(self,tax_period)
        this = self.env['account.iva.txt.export'].create({'state': 'get', 'data': content, 'name': name})
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'account.iva.txt.export',
            'view_mode': 'form',
            'view_type': 'form',
            'res_id': this.id,
            'views': [(False, 'form')],
            'target': 'new',
        }
        
    def create_attachment(self, content):
        ir_attachment = self.env['ir.attachment']
        value = {u'name': u'Reporte TXT de retención.txt',
                u'url': False,
                u'company_id': 1, 
                u'type': u'binary',
                u'public': False, 
                u'datas': content, 
                u'mimetype': 'txt',
                u'description': False}
        file_txt_id = ir_attachment.create(value)
        return file_txt_id
    
    def wh_refund_invoice(self,invoice_id):
        wh_lines = self.env['account.wh.iva.line'].search([('invoice_id', '=', invoice_id)])
        for whl in wh_lines:
            whl.refund=True
            #~ whl.state='annulled'
            #~ if self.state == 'done':
                
            #~ if self.state=='declared' and len(self.wh_lines) > 1:
                #~ wh_ids = self.search([('file_txt_id','=',self.file_txt_id.id)])
                #~ wh_list = map(lambda x: x.id, wh_ids)
                #~ self.env['account.wh.iva.declared'].create({'period':self.period,'wh_ids':[[6, False, wh_list]]}).to_declare_report_iva_txt()
        #~ acum = 0
        #~ for wh in self.wh_lines:
            #~ if wh.state=='annulled':
                #~ acum += 1
        #~ tax_ids = self.env['account.invoice.tax'].search(
                            #~ [('invoice_id', '=', invoice_id),
                            #~ ('amount', '>', 0)])
        #~ if len(self.wh_lines) == len(tax_ids) or acum == len(self.wh_lines):
            #~ self.state='annulled'
        return True
        
    #Columns
    journal_id = fields.Many2one('account.journal', string='Journal',
                                 required=True, readonly=True, states={'draft': [('readonly', False)]},
                                 default=_default_journal,
                                 domain="[('type', 'in', {'out_invoice': ['sale'], 'out_refund': ['sale'], 'in_refund': ['purchase'], 'in_invoice': ['purchase']}.get(type, [])), ('company_id', '=', company_id)]")
    number = fields.Char(
        string='Número de Comprobante', size=32, readonly=True,
        #~ states={'draft': [('readonly', False)]},
        help="Número de comprobante")
    type = fields.Selection([
            ('out_invoice','Customer Invoice'),
            ('in_invoice','Vendor Bill'),
            ('out_refund','Customer Refund'),
            ('in_refund','Vendor Refund'),
    ], string='Tipo', readonly=True,
        help="Tipo de retención")
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('withhold', 'Withhold'),
        ('declared', 'Declared'),
        ('done', 'Done'),
        ('annulled', 'Annulled'),
        ('cancel', 'Cancel')
    ], string='Estatus', readonly=True, default='draft',
        help="estatus de la retención")
    date = fields.Date(
        string='Date', readonly=True, required=True,
        default = fields.Date.context_today,
        states={'draft': [('readonly', False)]},
        help="Date of the issuance of the withholding document")
    account_id = fields.Many2one(
        'account.account', compute='_get_default_witholding_account', string='Cuenta', required=True, readonly=True,
        states={'draft': [('readonly', False)]}, #default = lambda self: if self.type == 'out_invoice' self.env.user.company_id.sale_iva_ret_account.id else self.env.user.company_id.purchase_iva_ret_account.id,
        help="Cuenta contable de la retención.")
    currency_id = fields.Many2one(
        'res.currency', string='Moneda', required=True, readonly=True,
        states={'draft': [('readonly', False)]}, help="Moneda",
        default=lambda self: self.env.user.company_id.currency_id.id)
    company_id = fields.Many2one(
        'res.company', string='Compañia', required=True, readonly=True,
        default=lambda self: self.env.company,
        # default=lambda self: self.env.user.company_id.id,
        help="Company")
    partner_id = fields.Many2one(
        'res.partner', string='Razón Social', readonly=True, required=True,
        states={'draft': [('readonly', False)]},
        help="Cliente o proveedor a retener")
    wh_lines = fields.One2many(
        'account.wh.iva.line', 'retention_id',
        string='Lineas de retención de iva', readonly=False,
        # states={'draft': [('readonly', False)]},
        help="Lineas de retención de IVA")
    total_tax_ret = fields.Monetary(
        string='Monto total retenido', digits=dp.get_precision('Withhold'),
        compute='_get_amount_total', 
        help="Calcula el monto total retenido de este comprobante")
    customer_doc_number = fields.Char(string="Nro Comprobante Cliente",
        help="Número de comprobante de retención emitido por el Cliente.")
    file_txt_id = fields.Many2many('ir.attachment',
        'account_wh_attachment_rel', 'wh_id', 'attachment_id', string="File TXT", copy=False, readonly=True)
    period = fields.Char(
        string='Tax Period', size=64, readonly=True,
        help="Tax Period")
    move_paid_id = fields.Many2one('account.move', 'Move Paid', 
                            readonly=True, 
                            copy=False, 
                            help="",)
    refund = fields.Boolean(string='Refund', default=False, help="")
    
    def action_withhold_iva_send(self):
        '''
        This function opens a window to compose an email, with the edi sale template message loaded by default
        '''
        self.ensure_one()
        ir_model_data = self.env['ir.model.data']
        try:
            template_id = ir_model_data.get_object_reference('l10n_ve_retencion_iva', 'email_template_wh_iva')[1]
        except ValueError:
            template_id = False
        try:
            compose_form_id = ir_model_data.get_object_reference('mail', 'email_compose_message_wizard_form')[1]
        except ValueError:
            compose_form_id = False
        ctx = dict()
        ctx.update({
            'default_model': 'account.wh.iva',
            'default_res_id': self.ids[0],
            'default_use_template': bool(template_id),
            'default_template_id': template_id,
            'default_composition_mode': 'comment',
            'custom_layout': "l10n_ve_retencion_iva.mail_template_data_notification_email_wh_iva"
        })
        return {
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(compose_form_id, 'form')],
            'view_id': compose_form_id,
            'target': 'new',
            'context': ctx,
        }
    
    def print_wh_iva_receipt(self):
        self.ensure_one()
        return self.env['report'].get_action(self, 'l10n_ve_retencion_iva.report_withholding_receipt_iva')

    @api.model
    def create(self, vals):
        wh_iva = super(AccountWhIva, self).create(vals)
        for wh in wh_iva.wh_lines:
            wh.invoice_id.write({'wh_id': wh_iva.id})
        # invoice = wh_iva.wh_lines.mapped(lambda l: l.invoice_id)
        # invoice.create_lines_retention(wh_iva)
        return wh_iva
    
    def write(self, vals):
        wh_iva = super(AccountWhIva, self).write(vals)
        self.search_tax_whlines()
        for inv in self:
            #revisar por que no esta declarado edit_iva; y wh_id es reconocido por un entero, no un string
            # self.env['account.move'].search([('wh_id', '=', inv.id )]).write({'wh_id':'', 'edit_iva':True})
            self.env['account.move'].search([('wh_id', '=', inv.id )]).write({'wh_id':False })
            for wh in inv.wh_lines:
                wh.invoice_id.write({'wh_id': inv.id})
        return wh_iva

    def unlink_lines(self):
        for inv in self.wh_lines:
            if inv.invoice_id.type in ('out_invoice', 'out_refund', 'out_receipt'):
                lines_retent = inv.invoice_id.env['account.move.line'].search([('account_id', '=', self.company_id.sale_iva_ret_account.id), ('move_id','=',inv.invoice_id.id)])
            else:
                lines_retent = inv.invoice_id.env['account.move.line'].search([('account_id', '=', self.company_id.purchase_iva_ret_account.id), ('move_id','=',inv.invoice_id.id)])
            line_payable = inv.invoice_id.line_ids.filtered(lambda line: line.account_id.user_type_id.type in ('receivable', 'payable'))

            for line in lines_retent:
                line_payable.with_context(check_move_validity=False).write({
                    'credit': line_payable['credit'] + line['credit'] if self.type not in ('out_invoice', 'out_receipt', 'in_refund') else 0.0,
                    'debit': line_payable['debit'] + line['debit'] if self.type in ('out_invoice', 'out_receipt', 'in_refund') else 0.0,
                })
            lines_retent.unlink()
    
    def unlink(self):
        for wh in self:
            if wh.state not in ('draft', 'cancel'):
                raise UserError(_('No puede eliminar retenciones confirmadas.'))
        self.unlink_lines()
        return super(AccountWhIva, self).unlink()
    
    
class AccountWhIvaLine(models.Model):
    _name = "account.wh.iva.line"
    _description = "Lineas de retención de IVA"

    @api.model
    def _get_ret_amount(self):
        for wh in self:
            round_curr = wh.retention_id.currency_id.round
            wh.ret_amount = round((wh.rate_amount * wh.amount_tax / 100), 2)

    @api.model
    def _get_sub_total(self):
        for wh in self:
            wh.sub_total = round(wh.base_tax + wh.amount_tax, 2)

    retention_id = fields.Many2one(
        'account.wh.iva', string='Vat Withholding',
        ondelete='cascade', help="Vat Withholding")
    invoice_id = fields.Many2one(
        'account.move', string='Factura', required=True, readonly=False,
        ondelete='restrict', help="Factura a retener")
    ret_tax = fields.Many2one('account.tax', string='Impuesto a retener', required=True,readonly=False,
        help="Impuesto a retener.")
    base_tax = fields.Float(string='Base Imponible', digits=dp.get_precision('Withhold'),readonly=False,
        help='Base imponible del impuesto')
    amount_tax = fields.Float(string='IVA Facturado', digits=dp.get_precision('Withhold'),
                              help="Monto a retener", readonly=False)
    rate_amount = fields.Float(string='% Retenido', digits=dp.get_precision('Withhold'), readonly=False,
                               help="Porcentaje aplicado al monto a retener")
    ret_amount = fields.Float(string='IVA Retenido', digits=dp.get_precision('Withhold'),
                              help="Monto a retener", readonly=False, compute='_get_ret_amount')
    sub_total = fields.Float(string='Total Compra', digits=dp.get_precision('Withhold'),
                              help="Total Compra", readonly=False, compute='_get_sub_total')
    move_id = fields.Many2one('account.move', 'Accounting Entry', readonly=False, copy=False)
    active = fields.Boolean('Active', default=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('withhold', 'Withhold'),
        ('declared', 'Declared'),
        ('done', 'Done'),
        ('annulled', 'Annulled'),
        ('cancel', 'Cancel')
    ], string='Status', readonly=True, default='draft',
        help="Status of Withholding")
    payments_three = fields.Boolean(string='Payments to third parties', default=False)

    def unlink(self):
        for wh in self:
            if wh.state!='draft':
                raise UserError(_('Una retención IVA declarada no puede ser eliminada.'))
                return
        return super(AccountWhIvaLine, self).unlink()


