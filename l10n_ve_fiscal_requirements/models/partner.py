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
import re

from odoo import models, fields, api
from odoo.exceptions import ValidationError

class ResPartner(models.Model):
    _inherit = "res.partner"

    vat = fields.Char(string="RIF/CI", required=False)
    # cedula = fields.Char(string="Cédula")
    street = fields.Char(required=True)
    city = fields.Char(required=True)
    state_id = fields.Many2one(required=True)
    country_id = fields.Many2one(required=True)
    residence_type = fields.Selection([('SR','Sin RIF'),
                                      ('R', 'Residenciado'),
                                      ('NR', 'No residenciado'),
                                      ('D', 'Domiciliado'),
                                      ('ND', 'No domiciliado')], help='This is the Supplier Type')

    
    @api.constrains('rif')
    def _check_rif(self):
        if self.rif:
            if self.company_type == 'company':
                formate = (r"[JG]{1}[-]{1}[0-9]{9}")
            else:
                formate = (r"[VE]{1}[-]{1}[0-9]{9}")
            form_rif = re.compile(formate)
            records = self.env['res.partner']
            rif_exist = records.search_count([('rif', '=', self.rif),('id', '!=', self.id)])
            for partner in self:
                if not form_rif.match(partner.rif):
                    if self.company_type == 'company':
                        raise ValidationError(("El formato del RIF es incorrecto por favor introduzca un RIF de la forma J-123456789 (utilice solo las letras J y G)"))
                    else:
                        raise ValidationError(("El formato del RIF es incorrecto por favor introduzca un RIF de la forma V-123456789 (utilice solo las letras V y E)"))
                #verificar si no existe un registro con el mismo rif
                elif rif_exist > 0:
                    raise ValidationError(
                        ("Ya existe un registro con este rif"))
                else:
                    return True

    @api.constrains('cedula')
    def _check_cedula(self):
        if self.cedula:
            formate = (r"[VEP]{1}[-]{1}[0-9]{8}")
            form_ci = re.compile(formate)
            records = self.env['res.partner']
            cedula_exist = records.search_count([('cedula', '=', self.cedula),('id', '!=', self.id)])
            for partner in self:
                if not form_ci.match(partner.cedula):
                    raise ValidationError(("El formato de la cedula es incorrecto. Por favor introduzca una cédula de la forma V-12345678"))
                elif cedula_exist > 0:
                    raise ValidationError(("Ya existe un registro con este número de cédula"))
                else:
                    return True
