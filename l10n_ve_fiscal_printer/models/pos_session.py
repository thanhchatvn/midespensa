# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging

from odoo import fields, models, _
from odoo.exceptions import Warning, UserError
from odoo.addons.l10n_ve_fiscal_printer.controllers import main_tfhka


_logger = logging.getLogger(__name__)


class PosSession(models.Model):
    _inherit = "pos.session"

    def print_z_report(self):
        try:
            main_printer = main_tfhka.Main()
            main_printer.open_port()
            main_printer.print_z_report()
        except Exception as e:
            _logger.warning('Exception Print Z Report: %s' % (e,))
            raise Warning(_('A problem has occurred with the printer: %s ') %(e,))

    def print_x_report(self):
        try:
            main_printer = main_tfhka.Main()
            main_printer.open_port()
            main_printer.print_x_report()
        except Exception as e:
            _logger.warning('Exception Print X Report: %s' % (e,))
            raise Warning(_('A problem has occurred with the printer: %s ') %(e,))

