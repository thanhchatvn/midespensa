# -*- coding: utf-8 -*-


from odoo import fields, models, api
from odoo.exceptions import UserError

class AccountWithholdingRateTable(models.Model):
    _name = 'account.withholding.rate.table'

    name = fields.Char('Información de la gaceta')
    year = fields.Integer("Year", required=True, default=lambda self: fields.Date.context_today(self).year)
    active = fields.Boolean('Active', default=True)
    factor = fields.Float('Factor')
    parcentage_subtracting_1 = fields.Float('Sustraendo 1%')
    parcentage_subtracting_3 = fields.Float('Sustraendo 3%')
    amount = fields.Float('Amount')
    state = fields.Selection([('draft','Draft'), ('confirmed','Confirmed')], string = 'State')
    line_ids = fields.One2many('account.withholding.rate.table.line', 'table_id', 'Tarifas')

class AccountWithholdingRateTableLine(models.Model):
    _name = 'account.withholding.rate.table.line'

    #Columns
    code = fields.Char('Code')
    concept = fields.Many2one('account.withholding.concept', 'Withholding', copy=False)
    residence_type = fields.Selection([
                                    ('R', 'Residenciado'),
                                    ('NR', 'No residenciado'),
                                    ('D', 'Domiciliado'),
                                    ('ND', 'No domiciliado'),
                                    ], 'Residence Type', copy=False)
    company_type = fields.Selection([
                                    ('person', 'Person'),
                                    ('company', 'Company'),
                                    ], 'Company Type', copy=False)
    percentage_amount_base = fields.Float('Percentage base retention')
    apply_up_to = fields.Float('Apply up to')
    percentage = fields.Float('Percentage retention')
    rate2 = fields.Boolean('Apply rate 2')
    variable = fields.Boolean('% de retencion Variable')
    table_id = fields.Many2one('account.withholding.rate.table', 'Retention table')




class AccountWithholdingConcept(models.Model):
    _name = 'account.withholding.concept'

    name = fields.Char('Concept')



