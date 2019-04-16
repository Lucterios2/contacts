# -*- coding: utf-8 -*-
'''
lucterios.contacts package

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

from django.utils.translation import ugettext_lazy as _
from django.utils import six

from lucterios.framework.tools import FORMTYPE_MODAL, MenuManage, CLOSE_NO, CLOSE_YES, WrapAction
from lucterios.framework.xfergraphic import XferContainerCustom, XferContainerAcknowledge
from lucterios.framework.xfercomponents import XferCompButton, XferCompImage, XferCompLabelForm, XferCompEdit
from lucterios.framework.xferadvance import TITLE_MODIFY, TITLE_OK, TITLE_CANCEL
from lucterios.framework.error import LucteriosException, IMPORTANT
from lucterios.framework import signal_and_lock

from lucterios.CORE.parameters import Params
from lucterios.CORE.views import ParamEdit

from lucterios.mailing.functions import will_mail_send, send_email, send_connection_by_email
from lucterios.contacts.models import LegalEntity


@MenuManage.describ('CORE.change_parameter', FORMTYPE_MODAL, 'contact.conf', _('Change mailing parameters'))
class Configuration(XferContainerCustom):
    icon = "config_mail.png"
    caption = _("Mailing parameters")

    def fillresponse(self):
        XferContainerCustom.fillresponse(self)
        self.new_tab(_('EMail configuration'))
        img = XferCompImage('img_conf')
        img.set_value(self.icon_path())
        img.set_location(0, 0, 1, 6)
        self.add_component(img)

        conf_params = ['mailing-smtpserver', 'mailing-smtpport',
                       'mailing-smtpsecurity', 'mailing-smtpuser', 'mailing-smtppass',
                       'mailing-dkim-private-path', 'mailing-dkim-selector',
                       'mailing-delay-batch', 'mailing-nb-by-batch']
        Params.fill(self, conf_params, 1, 1)
        btn = XferCompButton('editparam')
        btn.set_location(3, 1, 1, 5)
        btn.set_action(self.request, ParamEdit.get_action(_('Modify'), 'images/edit.png'), close=CLOSE_NO, params={'params': conf_params})
        self.add_component(btn)
        if will_mail_send():
            btn = XferCompButton('tryemail')
            btn.set_location(1, 10, 2)
            btn.set_action(self.request, SendEmailTry.get_action(_('Send'), ''), close=CLOSE_NO)
            self.add_component(btn)

        self.new_tab(_('Default message'))
        img = XferCompImage('img_msg')
        img.set_value(self.icon_path())
        img.set_location(0, 0, 1, 6)
        self.add_component(img)

        msg_params = ['mailing-msg-connection']
        Params.fill(self, msg_params, 1, 1)
        btn = XferCompButton('editmsg')
        btn.set_location(1, 10, 2)
        btn.set_action(self.request, ParamEdit.get_action(_('Modify'), 'images/edit.png'), close=CLOSE_NO, params={'params': msg_params})
        self.add_component(btn)


@MenuManage.describ('CORE.change_parameter')
class SendEmailTry(XferContainerAcknowledge):
    icon = "config_mail.png"
    caption = _("EMail try")

    def fillresponse(self):
        if not will_mail_send():
            raise LucteriosException(IMPORTANT, _('Bad email parameter!'))
        legal = LegalEntity.objects.get(id=1)
        if self.getparam('CONFIRME') is None:
            dlg = self.create_custom()
            img = XferCompImage('img')
            img.set_value(self.icon_path())
            img.set_location(0, 0, 1, 3)
            dlg.add_component(img)
            lbl = XferCompLabelForm('lbl_title')
            lbl.set_location(1, 0, 2)
            lbl.set_value_as_header(self.caption)
            dlg.add_component(lbl)
            email = XferCompEdit('recipient')
            email.set_location(1, 1)
            email.set_value(legal.email)
            email.mask = r"[^@]+@[^@]+\.[^@]+"
            email.description = _("email")
            dlg.add_component(email)
            dlg.add_action(self.get_action(TITLE_OK, "images/ok.png"), close=CLOSE_YES, params={'CONFIRME': 'YES'})
            dlg.add_action(WrapAction(TITLE_CANCEL, 'images/cancel.png'))
        else:
            address = []
            address.append("")
            address.append("")
            address.append(six.text_type(legal))
            address.append(legal.address)
            address.append("%s %s" % (legal.postal_code, legal.city))
            message = _('EMail sent to check configuration')
            message += "\n".join(address).replace('{[newline]}', "\n").replace('{[br/]}', "\n")
            send_email(self.getparam('recipient'), _("EMail try"), message)
            self.message(_("EMail send, check it."))


@signal_and_lock.Signal.decorate('send_connection')
def send_connection_email(email_adress, username, passwd):
    if will_mail_send():
        if email_adress and username and passwd:
            send_connection_by_email(email_adress, username, passwd)
        return True
    else:
        return False


@signal_and_lock.Signal.decorate('conf_wizard')
def conf_wizard_mailing(wizard_ident, xfer):
    if isinstance(wizard_ident, list) and (xfer is None):
        wizard_ident.append(("mailing_params", 52))
    elif (xfer is not None) and (wizard_ident == "mailing_params"):
        xfer.add_title(_("Lucterios mailing"), _("Mailing parameters"))
        lbl = XferCompLabelForm("nb_mail_send")
        lbl.set_location(1, xfer.get_max_row() + 1)
        xfer.add_component(lbl)
        if will_mail_send():
            lbl.set_value(_('email properly configured'))
        else:
            lbl.set_value(_('email not configured'))
        btn = XferCompButton("btnconf")
        btn.set_location(3, xfer.get_max_row())
        btn.set_action(xfer.request, Configuration.get_action(TITLE_MODIFY, "images/edit.png"), close=CLOSE_NO)
        xfer.add_component(btn)
