# -*- coding: utf-8 -*-

##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
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

{
    "name": "Modulo de integración con impresora fiscal",
    "version": "13.0.1",
    "author": "Soluciones Softhard C.A.",
    "category": "Localization",
    "description":
        """
Localización Venezolana: Municipios y Parroquias
================================================

Este modulo integra el POS con la impresora fiscal
     """,
    "website": "http://www.solucionesofthard.com/",
	'images': ['static/description/icon.png'],
    "depends": ['base','point_of_sale'],
    "init_xml": [],
    "demo_xml": [],
    "data": [
        'views/point_of_sale.xml',
        'views/pos_payment_method_views.xml',
        # 'views/pos_session_view.xml',

    ],
    'qweb': ["static/src/xml/*.xml"],
    "installable": True
}
