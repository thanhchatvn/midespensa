# -*- coding: utf-8 -*-


from odoo import fields, models, api
from odoo.exceptions import UserError


class AccountWithholdingRateTable(models.Model):
    _name = 'account.withholding.rate.table'

    name = fields.Char('Información de la gaceta')
    # year = fields.Integer("Year", required=True, default=lambda self: fields.Date.context_today(self).year)
    active = fields.Boolean('Active', default=True)
    factor = fields.Float('Factor', digits=(16, 4))
    rate2_ids = fields.One2many('rate.table.withholding', 'rate2_id', string='Rate Table 2')
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
    person_type = fields.Selection([
        ('PNR', 'PNR'),
        ('PNNR', 'PNNR'),
        ('PJD', 'PJD'),
        ('PJND', 'PJND')
    ])
    apply_up_to = fields.Float('Apply up to')
    percentage = fields.Float('Percentage retention')
    rate2 = fields.Boolean('Apply rate 2')
    apply_subtracting = fields.Boolean('Apply subtracting')
    variable = fields.Boolean('% de retencion Variable')
    table_id = fields.Many2one('account.withholding.rate.table', 'Retention table')


class RateTableWithholding(models.Model):
    _name = 'rate.table.withholding'

    lower_limit = fields.Float('Since U.T')
    percentage = fields.Float('Percentage')
    rate2_id = fields.Many2one('account.withholding.rate.table', 'Rate Table')
    upper_limit = fields.Float('Until U.T')
    subtracting = fields.Float('Subtracting U.T')


class AccountWithholdingConcept(models.Model):
    _name = 'account.withholding.concept'

    name = fields.Char('Concept')



