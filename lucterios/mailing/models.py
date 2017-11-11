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
from django.db import models
from django.apps import apps
from django_fsm import FSMIntegerField, transition

from lucterios.framework.models import LucteriosModel
from lucterios.framework.xfersearch import get_search_query_from_criteria
from lucterios.framework.tools import toHtml
from lucterios.mailing.functions import will_mail_send, send_email
from datetime import date
from lucterios.contacts.models import AbstractContact
from lucterios.CORE.models import Parameter
from lucterios.framework.signal_and_lock import Signal


class Message(LucteriosModel):
    subject = models.CharField(_('subject'), max_length=50, blank=False)
    body = models.TextField(_('body'), default="")
    status = FSMIntegerField(verbose_name=_('status'), default=0, choices=((0, _('open')), (1, _('close'))))
    recipients = models.TextField(_('recipients'), default="", null=False)
    date = models.DateField(verbose_name=_('date'), null=True)
    contact = models.ForeignKey('contacts.AbstractContact', verbose_name=_(
        'contact'), null=True, on_delete=models.SET_NULL)

    @classmethod
    def get_default_fields(cls):
        return ['status', 'date', 'subject']

    @classmethod
    def get_show_fields(cls):
        return [('status', 'date'), 'subject', 'recipients', 'body']

    @classmethod
    def get_edit_fields(cls):
        return ['subject', 'body']

    @classmethod
    def get_print_fields(cls):
        return ['status', 'date', 'subject', 'body', 'contact', 'OUR_DETAIL']

    def get_recipients(self):
        for item in self.recipients.split('\n'):
            if item != '':
                modelname, criteria = item.split(' ')
                yield modelname, get_search_query_from_criteria(criteria, apps.get_model(modelname))

    def get_contacts(self):
        id_list = []
        for modelname, item in self.get_recipients():
            for contact in apps.get_model(modelname).objects.filter(item[0]):
                id_list.append(contact.id)
        return AbstractContact.objects.filter(id__in=id_list)

    @property
    def recipients_description(self):
        for modelname, item in self.get_recipients():
            yield (apps.get_model(modelname)._meta.verbose_name.title(), " {[br/]}".join(item[1].values()))

    def add_recipient(self, modelname, criteria):
        if self.status == 0:
            self.recipients += modelname + ' ' + criteria + "\n"
            self.save()

    def del_recipient(self, recipients):
        if (self.status == 0) and (recipients >= 0):
            recipient_list = self.recipients.split('\n')
            if recipients < len(recipient_list):
                del recipient_list[recipients]
                self.recipients = "\n".join(recipient_list)
                self.save()

    transitionname__valid = _("Valid")

    @transition(field=status, source=0, target=1, conditions=[lambda item:item.recipients != ''])
    def valid(self):
        self.date = date.today()

    def send_email(self):
        nb_sent, nb_failed = 0, 0
        if will_mail_send():
            email_content = "<html><body>%s</body></html>" % toHtml(self.body)
            for contact in self.get_contacts():
                if contact.email != '':
                    try:
                        send_email(
                            [contact.email], self.subject, email_content)
                        nb_sent += 1
                    except:
                        nb_failed += 1
        return nb_sent, nb_failed

    class Meta(object):
        pass


@Signal.decorate('checkparam')
def mailing_checkparam():
    Parameter.check_and_create(name='mailing-smtpserver', typeparam=0, title=_("mailing-smtpserver"), args="{'Multi': False}", value='')
    Parameter.check_and_create(name='mailing-smtpport', typeparam=1, title=_("mailing-smtpport"), args="{'Min': 0, 'Max': 99999}", value='25')

    Parameter.check_and_create(name='mailing-smtpsecurity', typeparam=4, title=_("mailing-smtpsecurity"), args="{'Enum':3}", value='0',
                               param_titles=(_("mailing-smtpsecurity.0"), _("mailing-smtpsecurity.1"), _("mailing-smtpsecurity.2")))

    Parameter.check_and_create(name='mailing-smtpuser', typeparam=0, title=_("mailing-smtpuser"), args="{'Multi': False}", value='')

    Parameter.check_and_create(name='mailing-smtppass', typeparam=5, title=_("mailing-smtppass"), args="{'Multi': False}", value='')
    Parameter.check_and_create(name='mailing-msg-connection', typeparam=0, title=_("mailing-msg-connection"), args="{'Multi': True}",
                               value=_('''Connection confirmation to your application:
User:%(username)s
Password:%(password)s
'''))
