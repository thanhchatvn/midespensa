# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class PosOrder(models.Model):
    _inherit = "pos.order"

    printer_doc_number = fields.Char(string='Documento de la impresora',
        readonly=True, copy=False)

    # @api.model
    # def _order_fields(self, ui_order):
    #     fields = super(PosOrder, self)._order_fields(ui_order)
    #     fields['printer_doc_number'] = ui_order.get('printer_doc_number', False)
    #     return fields
    #
    # @api.model
    # def create_from_ui(self, orders, draft=False):
    #     order_ids = super(PosOrder, self).create_from_ui(orders)
    #     print('orders')
    #     print(orders)
    #     print('orders')
    #     print(order_ids)
    #     print('order_ids')
    #     for order in self.sudo().browse(order_ids):
    #         print('order')
    #         print('order')
    #         print(order)
    #         # print(order.printer_doc_number)
    #         print('order')
    #         print('order')
    #         print('order')
    #         # if order.loyalty_points != 0 and order.partner_id:
    #         #     order.partner_id.loyalty_points += order.loyalty_points
    #     return order_ids