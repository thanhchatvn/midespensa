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
from datetime import timedelta
from odoo.addons import decimal_precision as dp
from odoo import models, fields, api, exceptions, _
from odoo.tools import float_compare, float_is_zero
from odoo.exceptions import UserError

import xml.etree.ElementTree as ET
from io import StringIO, BytesIO
import base64

TYPE2JOURNAL = {
    'out_invoice': 'sale',
    'in_invoice': 'purchase',
    'out_refund': 'sale',
    'in_refund': 'purchase',
}

class AccountWhIslr(models.Model):
    _name = "account.wh.islr"
    _inherit = ['mail.thread']
    _rec_name="number"
    _description = "Withholding ISLR"
    _order = 'date desc, id desc'
    
    @api.model
    def name_get(self):
        for s in self:
            if not s.number:
                return [(s.id, "%s" % (s.name))]
        return super(AccountWhIslr, self).name_get()
    
    @api.depends('withholding_line.ret_amount','withholding_line.state','withholding_line')
    def _compute_amount(self):

        for line in self:
            line.amount_total = round(sum(line.withholding_line.filtered(lambda islr: islr.state != ['annulled','cancel']).mapped('ret_amount')), 2)

    @api.model
    def _default_journal(self):
        if self._context.get('default_journal_id', False):
            return self.env['account.journal'].browse(self._context.get('default_journal_id'))
        inv_type = self._context.get('type', 'out_invoice')
        inv_types = inv_type if isinstance(inv_type, list) else [inv_type]
        company_id = self._context.get('company_id', self.env.user.company_id.id)
        domain = [('company_id', '=', company_id)]
        return self.env['account.journal'].search(domain, limit=1)

    @api.onchange('partner_id')
    def _get_default_witholding_account(self):
        for wh in self:
            if wh.type == 'out_invoice':
                wh.account_id = wh.company_id.sale_islr_ret_account_id.id
            else:
                wh.account_id = wh.company_id.purchase_islr_ret_account_id.id
                wh.account_dec_id = wh.company_id.purchase_islr_ret_account_id.id
                
            
    name = fields.Char(
        string='Descripción', size=64, readonly=True,
        states={'draft': [('readonly', False)]}, required=True,
        help="Descripción de la retención")
    number = fields.Char(
        string='Número de Comprobante', size=32, readonly=True,
        states={'draft': [('readonly', False)]},
        help="Número de comprobante",)
    customer_doc_number = fields.Char(
        string='Nro Comprobante Cliente', size=32, readonly=True,
        states={'draft': [('readonly', False)]},
        help="Número de comprobante del cliente")
    type = fields.Selection([
            ('out_invoice','Customer Invoice'),
            ('in_invoice','Vendor Bill'),
            ('out_refund','Customer Refund'),
            ('in_refund','Vendor Refund'),
        ], string='Tipo', readonly=False,
        help="Tipo de retención")
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('declared', 'Declared'),
        ('done', 'Paid'),
        ('cancel', 'Cancelada'),
        ('annulled', 'Annulled')
        ], string='estatus', readonly=True, default='draft',
        help="estatus de la retención")
    date = fields.Date(
        string='Fecha', readonly=True,
        required=True,
        default = fields.Date.context_today,
        states={'draft': [('readonly', False)]},
        help="Fecha de la emisión del documento de retención")
    journal_id = fields.Many2one('account.journal', string='Journal',
        required=True, readonly=True, states={'draft': [('readonly', False)]},
        default=_default_journal,
        domain="[('type', 'in', {'out_invoice': ['sale'], 'out_refund': ['sale'], 'in_refund': ['purchase'], 'in_invoice': ['purchase']}.get(type, [])), ('company_id', '=', company_id)]")
    account_id = fields.Many2one(
        'account.account', compute='_get_default_witholding_account', string='Cuenta de retención', required=True, readonly=True,
        states={'draft': [('readonly', False)]},
        help="Cuenta contable de la retención.")
    company_id = fields.Many2one(
        'res.company', string='Compañia', required=True, readonly=True,
        default=lambda self: self.env.company,
        # default=lambda self: self.env.user.company_id.id,
        help="Company")
    partner_id = fields.Many2one(
        'res.partner', string='Razón Social', readonly=True, required=True,
        states={'draft': [('readonly', False)]},
        help="Cliente o proveedor a retener")
    currency_id = fields.Many2one('res.currency', 
                                string='Moneda', 
                                required=True, 
                                readonly=True,
                                default=lambda self: self.env.user.company_id.currency_id.id,
                                help="Moneda",)
    amount_total = fields.Monetary(string='Total', digits=dp.get_precision('Withhold'),
                                   readonly=True, compute='_compute_amount')
    percentage = fields.Float(string='Percentage', 
                        digits=dp.get_precision('Withhold'), 
                        required=False,
                        readonly=True,
                        states={'draft': [('readonly', False)]},
                        help="General percentage to apply the invoices" )
    code_withholding = fields.Char(string='Code', 
                                    required=False,
                                    readonly=True,
                                    states={'draft': [('readonly', False)]},
                                    help="Code the withholding" )
    withholding_line = fields.One2many('account.wh.islr.line', 'withholding_id', 
                                    string='Withholding Lines', 
                                    readonly=True,
                                    copy=True,
                                    states={'draft': [('readonly', False)]},
                                    )
    move_paid_id = fields.Many2one('account.move', 'Move Paid', 
                            readonly=True, 
                            copy=False, 
                            help="",)
    file_xml_id = fields.Many2many('ir.attachment', 'withholding_attachment_rel', 'withholding_id', 'attachment_id', string="File xml", copy=False, readonly=True)
    period = fields.Char(
                string='Period', size=64, readonly=True,
                help="Period the ithholding")
                
    
    def action_cancel_draft(self):
        for wh in self:
            for whl in wh.withholding_line:
                if whl.state=='withold':
                    raise UserError(_('Can not cancel a withholding with declared invoices.'))
                    return
            wh.state='cancel'
            for whl in wh.withholding_line:
                whl.invoice_id.withholding_line_id=False
                whl.invoice_id.withholding_id=False
            wh.withholding_line.unlink()

    def action_withold(self):
        for hw in self:
            if hw.withholding_line:
                if len(hw.withholding_line)==1:
                    if hw.withholding_line.state=='cancel':
                        raise UserError(_('There is no invoice to retain.'))
                        return
                for hwl in hw.withholding_line:
                    if hwl.state=='confirmed':
                        hwl.invoice_id.action_invoice_open()
        return self.write({'state':'withold'})
        
    def action_confirm(self):

        for hw in self:
            if hw.withholding_line:
                for hwl in hw.withholding_line:
                    if  hwl.ret_amount <= 0:
                        raise UserError(_('La retención del ISLR de cada factura debe ser mayor a 0.'))
                        return
            else:
                raise UserError(_('No se puede confirmar una retención sin asociar facturas.'))
                return
            hw.withholding_line.write({'state':'confirmed'})
        print('Metodo confirmar funciona')
        print('Metodo confirmar funciona')
        print('Metodo confirmar funciona')
        print('Metodo confirmar funciona')
        return self.write({'state':'confirmed','number':self.env['ir.sequence'].next_by_code('account.wh.islr.in_invoice') if self.type in ('in_invoice', 'in_refund') else ''})

    def action_confirm_2(self):
        '''
         Este metodo se usa para confirmar y no se genera correlativo.
        :return:
        '''
        for hw in self:
            if hw.withholding_line:
                for hwl in hw.withholding_line:
                    if  hwl.ret_amount <= 0:
                        raise UserError(_('La retención del ISLR de cada factura debe ser mayor a 0.'))
                        return
            else:
                raise UserError(_('No se puede confirmar una retención sin asociar facturas.'))
                return
            hw.withholding_line.write({'state':'confirmed'})
        return self.write({'state':'confirmed'})
    @api.model
    def action_withhold_islr_send(self):
        '''
        This function opens a window to compose an email, with the edi sale template message loaded by default
        '''
        self.ensure_one()
        ir_model_data = self.env['ir.model.data']
        try:
            template_id = ir_model_data.get_object_reference('l10n_ve_retencion_islr', 'email_template_wh_islr')[1]
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
            'custom_layout': "l10n_ve_retencion_islr.mail_template_data_notification_email_wh_islr"
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
    
    def generate_file_xml(self,withholding,period=None):
        if period==None:
            period=''
        company_id = withholding.company_id
        s=''
        if not company_id.vat:
            raise UserError(_("El RIF para la compañía no ha sido establecido o el registro se encuentra vacio, verifique nuevamente."))
        root = ET.Element("RelacionRetencionesISLR", RifAgente=s.join(company_id.vat.split('-')), Periodo=period)
        # ~ doc = ET.SubElement(root, "doc")
        for hw in withholding:
            if not hw.partner_id.vat:
                raise UserError(_("El Cliente o Proveedor %s no posee rif.") % hw.partner_id.name )
            rif=hw.partner_id.vat.split('-')
            rif=''.join(rif)
            code_withholding=hw.code_withholding
            for hwl in hw.withholding_line:
                date_invoice=hwl.invoice_id.invoice_date
                date_invoice='%s/%s/%s' % (date_invoice.year, date_invoice.month, date_invoice.day)
                if not hwl.invoice_id.control_invoice_number:
                    raise UserError(_(
                        "El Numero de control de la factura '%s' se encuentra vacio, verifique nuevamente.") % hwl.invoice_id.name)
                control_invoice_number=hwl.invoice_id.control_invoice_number.split('-')
                control_invoice_number=''.join(control_invoice_number)
                if hwl.state not in ['annulled','cancel']:
                    nodo1 = ET.SubElement(root, "DetalleRetencion")
                    nodo11 = ET.SubElement(nodo1, "RifRetenido")
                    nodo11.text = rif
                    nodo12 = ET.SubElement(nodo1, "NumeroFactura")
                    nodo12.text = hwl.invoice_id.vendor_invoice_number
                    nodo13 = ET.SubElement(nodo1, "NumeroControl")
                    nodo13.text = control_invoice_number
                    nodo14 = ET.SubElement(nodo1, "FechaOperacion")
                    nodo14.text = str(date_invoice)
                    nodo15 = ET.SubElement(nodo1, "CodigoConcepto")
                    nodo15.text = code_withholding
                    if hwl.invoice_id.type in ('in_refund'): #Si es nota de credito su valor es negativo
                        nodo16 = ET.SubElement(nodo1, "MontoOperacion")
                        nodo16.text = str('%.2f' % float(hwl.invoice_id.amount_untaxed*-1))
                    elif hwl.invoice_id.type not in ('in_refund'):
                        nodo16 = ET.SubElement(nodo1, "MontoOperacion")
                        nodo16.text = str('%.2f' % float(hwl.invoice_id.amount_untaxed))
                    nodo17 = ET.SubElement(nodo1, "PorcentajeRetencion")
                    nodo17.text = str(hwl.porc_islr)
        arbol = ET.ElementTree(root)
        return arbol
        
    def create_attachment(self,arbol):
        f = BytesIO()
        arbol.write(f)
        f.seek(0)
        file=f.read()
        # xml=file.encode("base64")
        xml=base64.encodebytes(bytes(file))
        ir_attachment=self.env['ir.attachment']
        value={u'name': u'Reporte Xml de retención.xml',
                u'url': False,
                u'company_id': 1,
                u'type': u'binary',
                u'public': False, 
                u'datas':xml ,
                u'mimetype': 'xml',
                u'description': False}
        file_xml_id=ir_attachment.create(value)
        return file_xml_id
    
    def action_declaration(self,context,massives=None):
        for wh in self:
            value={'state':'declared'}
            if massives==None:
                arbol=self.generate_file_xml(self)
                file_xml_id=self.create_attachment(arbol)
                value['file_xml_id']=[[6, False, [file_xml_id.id]]]
            self.write(value)
            # ~ wh_line=self.env['account.wh.islr.line'].search([('id','in',line_wh_ids)])
            wh.withholding_line.search([('withholding_id','=',wh.id),('state','not in',['annulled','cancel']),]).write({'state':'declared'})
            if massives==None:
                return {
                    'type': 'ir.actions.act_url',
                    'url': '/printReportIslr/%s' % self.id,
                    'target': 'self',
                    'res_id': self.id,
                        }
        return True

    @api.model
    def print_report_islr_pdf(self, *args):
        return self.env.ref['report'].report_action(self, 'l10n_ve_retencion_islr.report_islr')
            
    @api.model
    def print_report_islr_xml(self):
        return {
            'type': 'ir.actions.act_url',
            'url': '/printReportIslr/%s' % self.id,
            'target': 'self',
            'res_id': self.id,
                }
    
    def withholding_refund_invoice(self,withholding_line_id):
        #~ withholding_line_id.state='annulled'
        if self.state=='done':
            withholding_line_id.refund=True
        #~ if self.state=='declared' and len(self.withholding_line) > 1:
            #~ withholding_ids=self.search([('file_xml_id','=',self.file_xml_id.id)])
            #~ withholding_list=map(lambda x: x.id, withholding_ids )
            #~ self.env['account.declarate.islr'].create({'period':self.period,'withholding_ids':[[6, False, withholding_list]]}).print_declare_report_islr_xml()
        #~ acum=0
        #~ for wh in self.withholding_line:
            #~ if wh.state=='annulled':
                #~ acum+=1
        #~ if len(self.withholding_line)==1 or acum == len(self.withholding_line):
            #~ self.state='annulled'
        return True
    
    @api.model
    def print_withholding_receipt_xml(self,*args):
        # self.ensure_one()
        return self.env['report'].get_action(self, 'l10n_ve_retencion_islr.report_withholding_receipt')
    
    def button_dummy(self):
        return True
        
    @api.onchange('partner_id')
    def onchange_partner_id(self):
        self.withholding_line=False
    
    def unlink(self):
        for wh in self:
            if not wh.state in ['draft']:
                raise UserError(_('you can only cancel a withholding in draft status.'))
                return
        return super(AccountWhIslr, self).unlink()
        
    def create(self, vals):
        withholding_id=super(AccountWhIslr, self).create(vals)
        # withholding_id.withholding_line.invoice_id.create_lines_retentions(withholding_id)#Crea los apuntes contables
        for wh in withholding_id.withholding_line:
            wh.invoice_id.write({'withholding_id':withholding_id.id,'withholding_line_id':wh.id})
        return withholding_id

    def write(self, vals):
        withholding=super(AccountWhIslr, self).write(vals)
        for inv in self:
            self.env['account.move'].search([('withholding_id', '=', inv.id)]).write({'withholding_id':False,'withholding_line_id':False})
            for wh in inv.withholding_line:
                wh.invoice_id.write({'withholding_id':inv.id,'withholding_line_id':wh.id})
        return withholding

    

class AccountWhIslrLine(models.Model):
    _name = "account.wh.islr.line"
    _description = "Line invoice ISLR"

    descripcion = fields.Char(
        string='Descripción', size=64, readonly=True,
        help="Descripción de la factura")

    code_withholding_islr = fields.Char(string='Code',
                                   readonly=True,
                                   help="Code the withholding")
    withholding_id = fields.Many2one('account.wh.islr', 'Withholding',
                                    readonly=True, 
                                    copy=False)
    invoice_id = fields.Many2one('account.move', 
                                string='Factura', 
                                required=True,
                                ondelete='restrict',
                                readonly=True,
                                states={'draft': [('readonly', False)]},
                                help="Factura a retener")
    currency_id = fields.Many2one('res.currency', 
                                string='Moneda', 
                                required=True, 
                                readonly=True,
                                default=lambda self: self.env.user.company_id.currency_id.id,
                                help="Moneda",)
    amount_invoice = fields.Monetary(string='Monto Factura',
                                     # related='invoice_id.amount_untaxed',
                                     readonly=True,
                                     store=True,
                                     digits=dp.get_precision('Withhold'), 
                                     help="Factura a retener",
                                     )
    base_tax = fields.Float(string='Tax Base', digits=dp.get_precision('Withhold'), readonly=False,
                            help='Taxable base of the tax') #Base imponible
    porc_islr = fields.Float(string='% impuesto retenido', 
                        digits=dp.get_precision('Withhold'), 
                        required=True,
                        readonly=True,
                        states={'draft': [('readonly', False)]},
                        help="Porcentaje de impuesto retenido" )
    ret_amount = fields.Monetary(string='ISLR Retenido', 
                            digits=dp.get_precision('Withhold'), 
                            required=False,
                            readonly=True,
                            states={'draft': [('readonly', False)]},
                            compute='onchange_percentage_islr',
                            help="Monto a retener",)

    state = fields.Selection([
        ('draft', 'Borrador'),
        ('confirmed', 'Confirmed'),
        ('withold', 'Withold'),
         ('declared', 'Declarado'),
        ('done', 'Pagado'),
        ('cancel', 'Cancelada'),
        ('annulled', 'Annulled')
        ], string='Estatus', readonly=True, default='draft',
        help="estatus de linea de retención")
    refund = fields.Boolean(default=False, help="")
    edit_amount = fields.Boolean(default=False, string="Amount Manual",
                                readonly=True,
                                states={'draft': [('readonly', False)]},
                                help="")
    move_id = fields.Many2one('account.move', 'Move Retention', 
                            readonly=True, 
                            copy=False, 
                            help="",)
    
    # _sql_constraints = [
    #   ('ret_fact_uniq', 'unique (invoice_id)', 'La factura ya ha sido asginada a un'
    #      ' comprobante de retención.')]
    #
    
    @api.onchange('porc_islr')
    def onchange_percentage_islr(self):
        for porc in self:
            # porc.ret_amount = round(float((porc.amount_invoice*porc.porc_islr) / 100), 2) # Se basa en la base total
            porc.ret_amount = round(float((porc.invoice_id.amount_untaxed*porc.porc_islr) / 100), 2) #Se basa en la base imponible

        
    @api.onchange('invoice_id')
    def onchange_invoice_id(self):
        if not self.withholding_id.partner_id:
            raise UserError(_('You must select a Razón Social.'))
        return {'value':{'porc_islr':self.withholding_id.percentage}}
        
    
    @api.model
    def create(self, vals):
        withholding_id=super(AccountWhIslrLine, self).create(vals)
        if not self.edit_amount:
            withholding_id.ret_amount = round((withholding_id.amount_invoice*withholding_id.porc_islr)/100, 2)
        return withholding_id
        
    @api.model
    def write(self, vals):
        for wh in self:
            if not 'edit' in vals.keys():
                porc_islr=wh.porc_islr
                amount_invoice=wh.amount_invoice
                if 'porc_islr' in vals.keys():
                    porc_islr=vals['porc_islr']
                if 'amount_invoice' in vals.keys():
                    amount_invoice=vals['amount_invoice']
                if not wh.edit_amount:
                    vals['ret_amount'] =   round((amount_invoice*porc_islr)/100, 2)
        return super(AccountWhIslrLine, self).write(vals)
        
    @api.model
    def unlink(self):
        for wh in self:
            if not wh.state in ['draft','confirmed']:
                raise UserError(_('Una retención declarada no puede ser eliminada.'))
                return
        return super(AccountWhIslrLine, self).unlink()
        
    
class AccountInvoice(models.Model):
    _inherit = "account.move"
    
    pay_withholding_id = fields.Many2one('account.pays.islr', 'Pay Withholding', 
                                    readonly=True, 
                                    copy=False)
    
    @api.model
    def name_get(self):
        if 'withholding' in self._context.keys():
            return [(invoice.id, u'%s (N° %s)' % (invoice.name or "Factura de Proveedor", invoice.vendor_invoice_number)) for invoice in self]
        return super(AccountInvoice, self).name_get()
    
    withholding_id = fields.Many2one('account.wh.islr', 'Withholding ISLR', 
                                    readonly=True, 
                                    copy=False)
    withholding_line_id = fields.Many2one('account.wh.islr.line', 'Withholding ISLR line', 
                                    readonly=False, 
                                    copy=False)
    invoice_save = fields.Boolean(default=False, help="")
    amount_retention_islr = fields.Monetary(string='ISLR Retenido', 
                        related='withholding_line_id.ret_amount',
                        digits=dp.get_precision('Withhold'), 
                        required=False,
                        readonly=False,
                        help="Impuesto retenido" )
                                    
    @api.model
    def finalize_invoice_move_lines(self, move_lines):
        for inv in self:
            withholding=self.env['account.wh.islr.line'].search([('invoice_id', '=', inv.id )])
            if withholding:
                if inv.type in ['in_invoice']:
                    round_curr = inv.currency_id.round
                    company_currency = inv.company_id.currency_id
                    diff_currency = inv.currency_id != company_currency
                    for i in move_lines:
                        if int(i[2]['account_id'])==inv.account_id.id:
                            new_amount = round_curr(i[2]['credit']-withholding.ret_amount)
                            if inv.type in ['in_invoice']:
                                i[2]['credit'] = new_amount
                            move_line_islr =   {
                                          'analytic_account_id': False, 
                                          'tax_ids': False, 
                                          'name': 'Retención ISLR', 
                                          'analytic_tag_ids': False, 
                                          'product_uom_id': False, 
                                          'invoice_id': inv.id, 
                                          'analytic_line_ids': [], 
                                          'tax_line_id': False, 
                                          'currency_id': False, 
                                          'credit': round_curr(withholding.ret_amount), 
                                          'product_id': False, 
                                          'date_maturity':i[2]['date_maturity'] , 
                                          'debit': False, 
                                          'amount_currency': False, 
                                          'quantity': 1.0, 
                                          'partner_id': inv.partner_id.id, 
                                          'account_id': inv.withholding_id.account_id.id
                                                }   
                            move_lines.append((0,0,move_line_islr))
            if (inv.type=='in_refund' and inv.withholding_id):
                withholding_line=self.env['account.wh.islr.line'].search([('invoice_id', '=', inv.id )])
                for i in move_lines:
                    if int(i[2]['account_id'])==inv.account_id.id:
                        new_amount=i[2]['debit']-withholding_line.ret_amount
                        i[2]['debit']=new_amount
                        move_line_islr =   {
                                      'analytic_account_id': False, 
                                      'tax_ids': False, 
                                      'name': 'Retención ISLR', 
                                      'analytic_tag_ids': False, 
                                      'product_uom_id': False, 
                                      'invoice_id': inv.id, 
                                      'analytic_line_ids': [], 
                                      'tax_line_id': False, 
                                      'currency_id': False, 
                                      'credit': False, 
                                      'product_id': False, 
                                      'date_maturity':i[2]['date_maturity'] , 
                                      'debit': withholding_line.ret_amount, 
                                      'amount_currency': False, 
                                      'quantity': 1.0, 
                                      'partner_id': inv.partner_id.id, 
                                      'account_id': withholding_line.withholding_id.account_id.id
                                            }   
                        move_lines.append((0,0,move_line_islr))
        return super(AccountInvoice, self).finalize_invoice_move_lines(move_lines)
    
    def action_invoice_open(self):
        for inv in self:
            if inv.withholding_id:
                if inv.withholding_id.state!='confirmed':
                    raise UserError(_('You must confirm the associated withholding before you can validate the invoice.'))
                    return
                withholding_line=self.env['account.wh.islr.line'].search([('invoice_id', '=', inv.id )])
                if withholding_line.ret_amount<=0:
                    raise UserError(_('The retention of the ISLR must be greater than 0.'))
                    return
        invoice_open= super(AccountInvoice, self).action_invoice_open()
        for inv in self:
            if inv.withholding_id:
                withholding_line=self.env['account.wh.islr.line'].search([('invoice_id', '=', inv.id )])
                withholding_line.write({'move_id':inv.move_id.id,'state':'withold'})
        return invoice_open
    
    def action_invoice_cancel(self):
       invoice_cancel= super(AccountInvoice, self).action_invoice_cancel()
       for inv in self:
           if inv.withholding_id:
                if inv.withholding_id.state=='draft':
                    inv.withholding_id=''
                    inv.withholding_line_id=''
                elif inv.withholding_id.state in ['confirmed','withold']:
                    inv.withholding_line_id.state='cancel'
                    if len(inv.withholding_id.withholding_line)==1:
                        inv.withholding_id.state='cancel'
                        
                else:
                    raise UserError(_('The invoice is associated with a declared retention.'))
                    return
       return invoice_cancel
    
    def action_invoice_draft(self):
        for inv in self:
            if inv.withholding_id:
                if inv.withholding_id.state not in ['declared','done','annulled']:
                    inv.withholding_line_id.state='confirmed'
                    inv.withholding_id.state='confirmed'
                else:
                    raise UserError(_('The invoice is associated with a declared retention.'))
                    return
        return super(AccountInvoice, self).action_invoice_draft()
        
    @api.model
    def create(self, vals):
        vals['invoice_save']=True
        return super(AccountInvoice, self).create(vals)
    
    # def write(self, vals):
    #     for inv in self:
    #         if 'withholding_id' in vals.keys():
    #             if not vals['withholding_id'] and 'edit' not in vals.keys():
    #                     self.env['account.wh.islr.line'].search([('invoice_id', '=', inv.id )]).unlink()
    #             if vals['withholding_id']:
    #                 withholding=self.env['account.wh.islr'].search([('id', '=', int(vals['withholding_id']))])
    #                 withholding_line_obj=self.env['account.wh.islr.line']
    #                 withholding_line=withholding_line_obj.search([('invoice_id', '=', inv.id)])
    #                 value={u'currency_id':inv.currency_id.id , u'invoice_id': inv.id, u'ret_amount': 0, u'porc_islr': withholding.percentage,'withholding_id':withholding.id}
    #                 if not withholding_line:
    #                     withholding_line=withholding_line_obj.create(value)
    #                     vals['withholding_line_id']=withholding_line.id
    #                 else:
    #                     if withholding_line.withholding_id.id!=int(vals['withholding_id']):
    #                         withholding_line.unlink()
    #                         withholding_line=withholding_line_obj.create(value)
    #                         vals['withholding_line_id']=withholding_line.id
    #     invoice=super(AccountInvoice, self).write(vals)
    #     for wh in self:
    #         if wh.withholding_id:
    #             withholding=self.env['account.wh.islr.line'].search([('invoice_id', '=', wh.id )])
    #             if not withholding.edit_amount:
    #                 withholding.write({'ret_amount':round((wh.amount_untaxed*withholding.porc_islr)/100, 2)})
    #     return invoice

    @api.depends('state', 'journal_id', 'invoice_date')
    def _compute_invoice_sequence_number_next_(self):
        """ computes the prefix of the number that will be assigned to the first invoice/bill/refund of a journal, in order to
        let the user manually change it.
        """
        print("Estoy por aqui 1")
        # Check user group.
        system_user = self.env.is_system()
        if not system_user:
            self.invoice_sequence_number_next_prefix = False
            self.invoice_sequence_number_next = False
            return
        print('Estoy por aqui  2')
        # Check moves being candidates to set a custom number next.
        moves = self.filtered(lambda move: move.is_invoice() and move.name == '/')
        if not moves:
            self.invoice_sequence_number_next_prefix = False
            self.invoice_sequence_number_next = False
            return

        treated = self.browse()
        for key, group in groupby(moves, key=lambda move: (move.journal_id, move._get_sequence())):
            journal, sequence = key
            domain = [('journal_id', '=', journal.id), ('state', '=', 'posted')]
            if self.ids:
                domain.append(('id', 'not in', self.ids))
            if journal.type == 'sale':
                domain.append(('type', 'in', ('out_invoice', 'out_refund')))
            elif journal.type == 'purchase':
                domain.append(('type', 'in', ('in_invoice', 'in_refund')))
            else:
                continue
            if self.search_count(domain):
                continue

            for move in group:
                prefix, dummy = sequence._get_prefix_suffix(date=move.invoice_date or fields.Date.today(),
                                                            date_range=move.invoice_date)
                number_next = sequence._get_current_sequence().number_next_actual
                move.invoice_sequence_number_next_prefix = prefix
                move.invoice_sequence_number_next = '%%0%sd' % sequence.padding % number_next
                treated |= move
        remaining = (self - treated)
        remaining.invoice_sequence_number_next_prefix = False
        remaining.invoice_sequence_number_next = False

# ~ class AccountConfigSettingsInherit(models.TransientModel):
    # ~ _inherit = 'account.config.settings'
    
    
    # ~ retention_account_id = fields.Many2one('account.account',
                            # ~ related='company_id.purchase_islr_ret_account',
                            # ~ help="Account for defects for the retention of the ISLR")
    
    
# ~ class AccountInvoiceRefund(models.TransientModel):
    # ~ """Refunds invoice"""

    # ~ _inherit = "account.invoice.refund"
                                    
    # ~ @api.model
    # ~ def invoice_refund(self):
        # ~ inv_obj = self.env['account.move']
        # ~ context = dict(self._context or {})
        # ~ #~ for inv in inv_obj.browse(context.get('active_ids')):
            # ~ #~ if self.filter_refund == 'refund' and inv.withholding_id:
                # ~ #~ raise UserError(_('Option not available for invoices with associated retentions of ISLR.'))
                # ~ #~ return
        # ~ invoice_refund=super(AccountInvoiceRefund, self).invoice_refund()
        # ~ for inv in inv_obj.browse(context.get('active_ids')):
            # ~ if inv.withholding_id:
                # ~ inv.withholding_id.withholding_refund_invoice(inv.withholding_line_id)
        # ~ return invoice_refund

# ~ class AccountMoveReversal(models.TransientModel):
    # ~ _inherit = 'account.move.reversal'

    # ~ @api.model
    # ~ def reverse_moves(self):
        # ~ move_obj = self.env['account.move']
        # ~ inv_obj = self.env['account.invoice']
        # ~ context = dict(self._context or {})
        # ~ for mov in move_obj.browse(context.get('active_ids')):
            # ~ invoice_id=inv_obj.search([('move_id','=',mov.id)])
            # ~ if invoice_id.withholding_id:
                # ~ invoice_id.withholding_id.withholding_refund_invoice(invoice_id.withholding_line_id)
        # ~ return super(AccountMoveReversal, self).reverse_moves()
