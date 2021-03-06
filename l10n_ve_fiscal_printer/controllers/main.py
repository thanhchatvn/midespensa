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
# Generated by the Odoo plugin for Dia !
#

# from PyQt4.QtGui import QApplication, QMainWindow
# from PyQt4.QtCore import *
# from PyQt4.QtGui import *
# from PyQt4 import uic
from datetime import (timedelta, datetime as pyDateTime, date as pyDate, time as pyTime)

import os, sys, stat
import time
import subprocess

from odoo import http, _
from . import main_tfhka


class PrinterController(http.Controller):

    @http.route('/pos/fiscal_printer', type='json', auth='none', cors='*')
    def default_printer_action(self, **data):
        # print('jeison')
        # print('jeison')
        data['data']['company'].pop('logo')
        print(data)
        # print(data['data']['name'])
        # print('jeison')
        # print('jeison')
        # print('jeison')
        # print(ssss)

        # os.chmod("/dev/ttyACM0", stat.S_IXGRP)
        # subprocess.call(['chmod', '-R', '+w', '/dev/ttyACM0'])

        # st = os.stat('/dev/ttyACM0')
        # os.chmod('/dev/ttyACM0', st.st_mode |
        # uid = pwd("jpernia")[2]
        # gid = grp.getgrnam("jpernia")[2]
        # os.chown("/dev/ttyACM0", uid, gid)

        # os.chmod(
        #     '/dev/ttyACM0',
        #     stat.S_IRUSR |
        #     stat.S_IWUSR |
        #     stat.S_IRGRP |
        #     stat.S_IWGRP |
        #     stat.S_IROTH
        # )

        #
        # # print(data)
        # print(da)
        main_printer = main_tfhka.Main()
        main_printer.open_port()
        # main_printer.factura(data)
        main_printer.print_customer_invoice(data)
        # main_printer.send_cmd('D')