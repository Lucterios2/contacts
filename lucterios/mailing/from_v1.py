# -*- coding: utf-8 -*-
'''
from_v1 module for contacts

@author: Laurent GAY
@organization: sd-libre.fr
@contact: info@sd-libre.fr
@copyright: 2015 sd-libre.fr
@license: This file is part of Lucterios.

Lucterios is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

Lucterios is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with Lucterios.  If not, see <http://www.gnu.org/licenses/>.
'''

from __future__ import unicode_literals

from lucterios.install.lucterios_migration import MigrateAbstract


class MailingMigrate(MigrateAbstract):

    def _params(self):
        from lucterios.CORE.models import Parameter
        cur_p = self.old_db.open()
        cur_p.execute(
            "SELECT paramName,value FROM CORE_extension_params WHERE extensionId LIKE 'org_lucterios_contacts' and paramName in ('MailSmtpServer','MailSmtpPort','MailSmtpSecurity','MailSmtpUser','MailSmtpPass','MailConnectionMsg')")
        for param_name, param_value in cur_p.fetchall():
            pname = ''
            if param_name == 'MailSmtpServer':
                pname = 'mailing-smtpserver'
            if param_name == 'MailSmtpPort':
                pname = 'mailing-smtpport'
                if param_value == '':
                    param_value = '25'
            if param_name == 'MailSmtpSecurity':
                pname = 'mailing-smtpsecurity'
            if param_name == 'MailSmtpUser':
                pname = 'mailing-smtpuser'
            if param_name == 'MailSmtpPass':
                pname = 'mailing-smtppass'
            if param_name == 'MailConnectionMsg':
                pname = 'mailing-msg-connection'
            if pname != '':
                self.print_debug(
                    "=> parameter of mailing %s - %s", (pname, param_value))
                Parameter.change_value(pname, param_value)

    def run(self):
        try:
            self._params()
        finally:
            self.old_db.close()
        return
