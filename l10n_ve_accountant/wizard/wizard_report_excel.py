# -*- coding: utf-8 -*-

from odoo import fields, models, _

class BookExportExcel(models.TransientModel):
    _name = 'book.export.excel'
    _description = 'Export Excel'

    excel_file = fields.Binary('Descargar')
    file_name = fields.Char('Descargar')
