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
from datetime import date, datetime
import json

from django.utils.translation import ugettext_lazy as _
from django.db import models
from django.apps import apps
from django_fsm import FSMIntegerField, transition
from django.utils import six, formats, timezone

from lucterios.framework.models import LucteriosModel, LucteriosScheduler
from lucterios.framework.xfersearch import get_search_query_from_criteria
from lucterios.framework.tools import toHtml
from lucterios.framework.signal_and_lock import Signal
from lucterios.CORE.models import Parameter
from lucterios.CORE.parameters import Params
from lucterios.contacts.models import AbstractContact
from lucterios.documents.models import Document
from lucterios.mailing.functions import will_mail_send, send_email


class Message(LucteriosModel):
    subject = models.CharField(_('subject'), max_length=50, blank=False)
    body = models.TextField(_('body'), default="")
    status = FSMIntegerField(verbose_name=_('status'), default=0, choices=((0, _('open')), (1, _('valided')), (2, _('sending'))))
    recipients = models.TextField(_('recipients'), default="", null=False)
    date = models.DateField(verbose_name=_('date'), null=True)
    contact = models.ForeignKey('contacts.AbstractContact', verbose_name=_('contact'), null=True, on_delete=models.SET_NULL)
    email_to_send = models.TextField(_('email to send'), default="")
    documents = models.ManyToManyField(Document, verbose_name=_('documents'), blank=True)

    def __init__(self, *args, **kwargs):
        LucteriosModel.__init__(self, *args, **kwargs)
        self._show_only_failed = False

    def set_context(self, xfer):
        self._show_only_failed = xfer.getparam('show_only_failed', False)

    @property
    def emailsent_query(self):
        if self._show_only_failed:
            return models.Q(success=False)
        else:
            return models.Q()

    @classmethod
    def get_default_fields(cls):
        return ['status', 'date', 'subject', (_('number of contacts'), 'contact_nb')]

    @classmethod
    def get_show_fields(cls):
        return {'': [('status', 'date'), 'subject', 'body'],
                _('001@Recipients'): ['recipients', ((_('number of contacts'), 'contact_nb'), (_('without email address'), 'contact_noemail'))],
                _('002@Documents'): ['documents', (('', 'empty'),)]
                }
#         return [('status', 'date'), 'recipients',
#                 ((_('number of contacts'), 'contact_nb'), (_('without email address'), 'contact_noemail')),
#                 'documents', 'subject', 'body']

    @property
    def empty(self):
        return ""

    @property
    def contact_nb(self):
        return len(self.get_contacts())

    @property
    def contact_noemail(self):
        no_emails = self.get_contacts(False)
        return '{[br/]}'.join([six.text_type(no_email) for no_email in no_emails])

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

    def get_contacts(self, email=None):
        id_list = []
        for modelname, item in self.get_recipients():
            contact_filter = item[0]
            if email is not None:
                contact_filter &= ~models.Q(email='') if email else models.Q(email='')
            for contact in apps.get_model(modelname).objects.filter(contact_filter):
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

    transitionname__sending = _("Emails")

    @transition(field=status, source=1, target=2, conditions=[lambda item:will_mail_send()])
    def sending(self):
        if will_mail_send():
            email_list = []
            for contact in self.get_contacts(True):
                for email1 in contact.email.split(';'):
                    for email2 in email1.split(','):
                        if (":%s|" % email2) not in ("|".join(email_list) + '|'):
                            email_list.append("%d:%s" % (contact.id, email2))
            self.email_to_send = "\n".join(email_list)
            self.save()
            self.emailsent_set.all().delete()
            add_mailing_in_scheduler(check_nb=False)
        return

    def sendemail(self, nb_to_send):
        if will_mail_send() and (self.status == 2):
            email_list = self.email_to_send.split("\n")
            email_content = "<html><body>%s</body></html>" % toHtml(self.body)
            files = []
            for doc in self.documents.all():
                files.append((doc.name, doc.content))
            for contact_email in email_list[:nb_to_send]:
                contact_id, email = contact_email.split(':')
                try:
                    contact = AbstractContact.objects.get(id=contact_id)
                except AbstractContact.DoesNotExist:
                    contact = None
                try:
                    send_email([email], self.subject, email_content, files=files if len(files) > 0 else None)
                    EmailSent.objects.create(message=self, contact=contact, email=email, date=timezone.now(), success=True)
                except Exception as error:
                    EmailSent.objects.create(message=self, contact=contact, email=email, date=timezone.now(), success=False, error=six.text_type(error))
            self.email_to_send = "\n".join(email_list[nb_to_send:])
            if self.email_to_send == '':
                self.status = 1
            self.save()
        return

    def get_email_status(self):
        if not hasattr(self, '_email_status'):
            self._email_status = json.loads(self.email_sent)
        return self._email_status

    @property
    def date_begin(self):
        emails_sent = self.emailsent_set.order_by('date')
        if len(emails_sent) > 0:
            return formats.date_format(emails_sent[0].date, "DATETIME_FORMAT")
        return '---'

    @property
    def date_end(self):
        emails_sent = self.emailsent_set.order_by('-date')
        if len(emails_sent) > 0:
            return formats.date_format(emails_sent[0].date, "DATETIME_FORMAT")
        return '---'

    class Meta(object):
        verbose_name = _('message')
        verbose_name_plural = _('messages')


class EmailSent(LucteriosModel):
    message = models.ForeignKey(Message, verbose_name=_('message'), null=False, on_delete=models.CASCADE)
    contact = models.ForeignKey('contacts.AbstractContact', verbose_name=_('contact'), null=True, on_delete=models.SET_NULL)
    email = models.CharField(_('email'), max_length=50, blank=False)
    date = models.DateTimeField(verbose_name=_('date'), null=True)
    success = models.BooleanField(verbose_name=_('success'), default=False)
    error = models.TextField(_('error'), default="")

    @classmethod
    def get_default_fields(cls):
        return ['contact', 'email', 'date', 'success', 'error']

    class Meta(object):
        verbose_name = _('email sent info')
        verbose_name_plural = _('email sent info')
        default_permissions = []
        ordering = ['date', 'email']


def send_mailing_in_waiting():
    '''Mailing'''
    msg_list = Message.objects.filter(status=2)
    if len(msg_list) == 0:
        LucteriosScheduler.remove(send_mailing_in_waiting)
    else:
        for msg_item in msg_list:
            msg_item.sendemail(Params.getvalue('mailing-nb-by-batch'))


def add_mailing_in_scheduler(check_nb=True):
    if not check_nb or (Message.objects.filter(status=2).count() > 0):
        LucteriosScheduler.add_task(send_mailing_in_waiting, minutes=Params.getvalue('mailing-delay-batch'))


@Signal.decorate('checkparam')
def mailing_checkparam():
    Parameter.check_and_create(name='mailing-smtpserver', typeparam=0, title=_("mailing-smtpserver"), args="{'Multi': False}", value='')
    Parameter.check_and_create(name='mailing-smtpport', typeparam=1, title=_("mailing-smtpport"), args="{'Min': 0, 'Max': 99999}", value='25')

    Parameter.check_and_create(name='mailing-smtpsecurity', typeparam=4, title=_("mailing-smtpsecurity"), args="{'Enum':3}", value='0',
                               param_titles=(_("mailing-smtpsecurity.0"), _("mailing-smtpsecurity.1"), _("mailing-smtpsecurity.2")))

    Parameter.check_and_create(name='mailing-smtpuser', typeparam=0, title=_("mailing-smtpuser"), args="{'Multi': False}", value='')

    Parameter.check_and_create(name='mailing-smtppass', typeparam=5, title=_("mailing-smtppass"), args="{'Multi': False}", value='')
    Parameter.check_and_create(name='mailing-msg-connection', typeparam=0, title=_("mailing-msg-connection"), args="{'Multi': True, 'HyperText': True}",
                               value=_('''Connection confirmation to your application:{[br/]} - User:%(username)s{[br/]} - Password:%(password)s{[br/]}'''))
    Parameter.check_and_create(name='mailing-delay-batch', typeparam=2, title=_("mailing-delay-batch"), args="{'Min': 0.1, 'Max': 120, 'Prec': 1}", value='15')
    Parameter.check_and_create(name='mailing-nb-by-batch', typeparam=1, title=_("mailing-nb-by-batch"), args="{'Min': 1, 'Max': 100}", value='10')
