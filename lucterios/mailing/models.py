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
from datetime import date
from html2text import HTML2Text
from logging import getLogger, DEBUG
from _io import BytesIO
import json

from django.utils.translation import ugettext_lazy as _
from django.db import models
from django.db.models.query import QuerySet
from django.apps import apps
from django_fsm import FSMIntegerField, transition
from django.utils import six, formats, timezone

from lucterios.framework.models import LucteriosModel, LucteriosScheduler,\
    LucteriosVirtualField
from lucterios.framework.xfersearch import get_search_query_from_criteria
from lucterios.framework.printgenerators import ReportingGenerator
from lucterios.framework.tools import toHtml, get_date_formating
from lucterios.framework.signal_and_lock import Signal
from lucterios.framework.error import LucteriosException, GRAVE
from lucterios.framework.filetools import remove_accent
from lucterios.CORE.models import Parameter, PrintModel
from lucterios.CORE.parameters import Params

from lucterios.contacts.models import AbstractContact
from lucterios.documents.models import DocumentContainer
from lucterios.documents.models_legacy import Document
from lucterios.mailing.functions import will_mail_send, send_email
from locale import format_string
from lucterios.framework.auditlog import auditlog


class MessageLine(LucteriosModel):
    id = models.IntegerField(verbose_name=_('id'), null=False, default=0, db_index=True)
    line = models.TextField(_('line'), null=False, default="")

    @classmethod
    def get_default_fields(cls, status=-1):
        return ['line']

    class Meta(object):
        abstract = True
        verbose_name = _('body')
        verbose_name_plural = _('bodies')


class MessageLineSet(QuerySet):

    def __init__(self, model=None, query=None, using=None, hints=None):
        QuerySet.__init__(self, model=MessageLine, query=query, using=using, hints=hints)
        self._result_cache = None
        self.pt_id = 0
        self.model._meta.pk = Message()._meta.pk
        body = self._hints['body']
        body = body.replace('\n', '')
        body = body.replace('{[br]}', '{[br/]}')
        body = body.replace('{[p]}', '')
        body = body.replace('{[/p]}', '\n')
        self.lines = body.split('\n')

    def _fetch_all(self):
        if self._result_cache is None:
            self._result_cache = []
            line_id = 1
            for line in self.lines:
                self._result_cache.append(MessageLine(id=line_id, line=line))
                line_id += 1


class Message(LucteriosModel):
    subject = models.CharField(_('subject'), max_length=50, blank=False)
    body = models.TextField(_('body'), default="")
    status = FSMIntegerField(verbose_name=_('status'), default=0, choices=((0, _('open')), (1, _('valided')), (2, _('sending'))))
    recipients = models.TextField(_('recipients'), default="", null=False)
    date = models.DateField(verbose_name=_('date'), null=True)
    contact = models.ForeignKey('contacts.AbstractContact', verbose_name=_('contact'), null=True, on_delete=models.SET_NULL)
    email_to_send = models.TextField(_('email to send'), default="")
    documents = models.ManyToManyField(Document, verbose_name=_('documents'), blank=True)
    attachments = models.ManyToManyField(DocumentContainer, verbose_name=_('documents'), blank=True)
    doc_in_link = models.BooleanField(_('documents in link'), null=False, default=False)
    contact_nb = LucteriosVirtualField(verbose_name=_('number of recipients'), compute_from='get_contact_nb', format_string='N')
    contact_noemail = LucteriosVirtualField(verbose_name=_('without email address'), compute_from='get_contact_noemail')

    def __init__(self, *args, **kwargs):
        LucteriosModel.__init__(self, *args, **kwargs)
        self._show_only_failed = False
        self._last_xfer = None

    def set_context(self, xfer):
        self._show_only_failed = xfer.getparam('show_only_failed', False)
        self._last_xfer = xfer

    @property
    def emailsent_query(self):
        if self._show_only_failed:
            return models.Q(success=False)
        else:
            return models.Q()

    @classmethod
    def get_default_fields(cls):
        return ['status', 'date', 'subject', 'contact_nb']

    @classmethod
    def get_show_fields(cls):
        return {'': [('status', 'date')],
                _('001@Message'): ['subject', 'body'],
                _('002@Recipients'): ['recipients', ('contact_nb', 'contact_noemail')],
                _('003@Documents'): ['attachments', (('', 'empty'),), 'doc_in_link']
                }

    @property
    def empty(self):
        return ""

    def get_contact_nb(self):
        return len(self.get_contacts())

    @property
    def line_set(self):
        return MessageLineSet(hints={'body': self.body})

    def get_contact_noemail(self):
        no_emails = self.get_contacts(False)
        return [six.text_type(no_email) for no_email in no_emails]

    @classmethod
    def get_edit_fields(cls):
        return ['subject', 'body', 'doc_in_link']

    @classmethod
    def get_print_fields(cls):
        return ['status', 'date', 'subject', 'body', 'line_set', 'line_set.line', 'contact', 'OUR_DETAIL']

    def get_recipients(self):
        for item in self.recipients.split('\n'):
            if item != '':
                modelname, criteria = item.split(' ')
                yield modelname, get_search_query_from_criteria(criteria, apps.get_model(modelname))

    def get_contacts(self, email=None):
        def append_contact(new_contact):
            if new_contact not in contact_list:
                contact_list.append(new_contact)
        contact_list = []
        for modelname, item in self.get_recipients():
            model = apps.get_model(modelname)
            contact_filter = item[0]
            if (email is not None) and (model.get_field_by_name('email') is None):
                for contact in model.objects.filter(contact_filter).distinct():
                    if (email is True) and hasattr(contact, 'get_email') and (contact.get_email() != []):
                        append_contact(contact)
                    elif (email is False) and (not hasattr(contact, 'get_email') or (contact.get_email() == [])):
                        append_contact(contact)
            else:
                if (email is not None) and (model.get_field_by_name('email') is not None):
                    contact_filter &= ~models.Q(email='') if email else models.Q(email='')
                for contact in model.objects.filter(contact_filter).distinct():
                    append_contact(contact)
        return contact_list

    @property
    def recipients_description(self):
        for modelname, item in self.get_recipients():
            model = apps.get_model(modelname)
            yield (model._meta.verbose_name.title(), " {[br/]}".join(item[1].values()))

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

    def get_printmodel_names(self):
        printmodel_name = {}
        for last_sending_item in self.email_to_send.split('\n'):
            if len(last_sending_item.split(':')) == 3:
                printmodel_name[last_sending_item.split(':')[0]] = last_sending_item.split(':')[2]
        for old_emailsent in self.emailsent_set.all():
            last_sending_item = old_emailsent.email
            if len(last_sending_item.split(':')) == 3:
                printmodel_name[last_sending_item.split(':')[0]] = last_sending_item.split(':')[2]
        return printmodel_name

    @property
    def is_dynamic(self):
        return len(self.get_printmodel_names()) > 0

    def _prep_sending(self):
        email_list = []
        printmodel_name = self.get_printmodel_names()
        for contact in self.get_contacts(True):
            if len(printmodel_name) == 0:
                for email1 in contact.email.split(';'):
                    for email2 in email1.split(','):
                        if (":%s|" % email2) not in ("|".join(email_list) + '|'):
                            email_list.append("%d:%s" % (contact.id, email2))
            else:
                model_name = contact.__class__.get_long_name()
                email_list.append("%s:%d:%s" % (model_name, contact.id, printmodel_name[model_name] if model_name in printmodel_name.keys() else "0"))
        self.email_to_send = "\n".join(email_list)
        self.save()
        self.emailsent_set.all().delete()

    transitionname__sending = _("Emails")

    @transition(field=status, source=1, target=2, conditions=[lambda item:will_mail_send()])
    def sending(self):
        if will_mail_send():
            self._prep_sending()
            if self._last_xfer is not None:
                abs_url = self._last_xfer.request.META.get('HTTP_REFERER', self._last_xfer.request.build_absolute_uri()).split('/')
                root_url = '/'.join(abs_url[:-2])
            else:
                root_url = ''
            getLogger('lucterios.mailing').debug('Message.sending() -> add_mailing_in_scheduler(http_root_address=%s)', root_url)
            add_mailing_in_scheduler(check_nb=False, http_root_address=root_url)
        return

    def define_email_message(self):
        if not hasattr(self, 'http_root_address'):
            raise LucteriosException(GRAVE, "No http_root_address")
        link_html = ""
        self._attache_files = []
        for doc in self.attachments.all():
            if self.doc_in_link:
                if doc.sharekey is None:
                    doc.change_sharekey(False)
                    doc.save()
                doc.set_context(self.http_root_address)
                link_html += "<li><a href='%s'>%s</a></li>" % (doc.shared_link, doc.name)
            else:
                self._attache_files.append((doc.name, doc.content))
        if self.doc_in_link and (link_html != ''):
            link_html = "<hr/><h3>%s</h3><ul>%s</ul>" % (_('Shared documents'), link_html)
        self._email_content = "<html><body>%s%s</body></html>" % (toHtml(self.body), link_html)

    @property
    def email_content(self):
        if not hasattr(self, '_email_content'):
            self.define_email_message()
        return self._email_content

    @property
    def attach_files(self):
        if not hasattr(self, '_attache_files'):
            self.define_email_message()
        return self._attache_files

    def sendemail(self, nb_to_send, http_root_address):
        getLogger('lucterios.mailing').debug('Message.sendemail(nb_to_send=%s, http_root_address=%s)', nb_to_send, http_root_address)
        self.http_root_address = http_root_address
        if will_mail_send() and (self.status == 2):
            email_list = self.email_to_send.split("\n")
            for contact_email in email_list[:nb_to_send]:
                contact_email_det = contact_email.split(':')
                if len(contact_email_det) == 2:
                    contact_id, email = contact_email_det
                    try:
                        contact = AbstractContact.objects.get(id=contact_id)
                    except AbstractContact.DoesNotExist:
                        contact = None
                elif len(contact_email_det) == 3:
                    modelname, object_id, _printmodel = contact_email_det
                    model = apps.get_model(modelname)
                    item = model.objects.get(id=object_id)
                    if hasattr(item, 'contact'):
                        contact = item.contact
                    elif isinstance(item, AbstractContact):
                        contact = item
                    else:
                        contact = None
                    email = contact_email
                else:
                    continue
                email_sent = EmailSent.objects.create(message=self, contact=contact, email=email, date=timezone.now())
                email_sent.send_email(http_root_address)
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
            return get_date_formating(emails_sent[0].date)
        return '---'

    @property
    def date_end(self):
        emails_sent = self.emailsent_set.order_by('-date')
        if len(emails_sent) > 0:
            return get_date_formating(emails_sent[0].date)
        return '---'

    @property
    def nb_total(self):
        return self.emailsent_set.all().count()

    @property
    def nb_errors(self):
        return self.emailsent_set.filter(success=False).count()

    @property
    def nb_open(self):
        return self.emailsent_set.filter(last_open_date__isnull=False).count()

    @property
    def statistic(self):
        return _('Send = %(send)d at %(date)s - Error = %(error)d - Open = %(open)d => %(ratio).1f %%') % {
            'send': self.nb_total,
            'date': self.date_end,
            'error': self.nb_errors,
            'open': self.nb_open,
            'ratio': (100.0 * self.nb_open) / self.nb_total
        }

    class Meta(object):
        verbose_name = _('message')
        verbose_name_plural = _('messages')
        ordering = ['-date']


class EmailSent(LucteriosModel):
    message = models.ForeignKey(Message, verbose_name=_('message'), null=False, on_delete=models.CASCADE)
    contact = models.ForeignKey('contacts.AbstractContact', verbose_name=_('contact'), null=True, on_delete=models.SET_NULL)
    email = models.CharField(_('email'), max_length=50, blank=False)
    date = models.DateTimeField(verbose_name=_('date'), null=True)
    success = models.BooleanField(verbose_name=_('success'), default=False)
    error = models.TextField(_('error'), default="")
    last_open_date = models.DateTimeField(verbose_name=_('last open date'), null=True, default=None)
    nb_open = models.IntegerField(verbose_name=_('number open'), null=False, default=0)
    sended_item = LucteriosVirtualField(verbose_name=_('sended item'), compute_from='get_sended_item')

    @classmethod
    def get_default_fields(cls):
        return ['contact', 'sended_item', 'date', 'success', 'error', 'last_open_date', 'nb_open']

    def get_send_email_objects(self):
        return [self.item]

    def get_sended_item(self):
        if len(self.email.split(':')) == 3:
            modelname, object_id, _printmodel = self.email.split(':')
            model = apps.get_model(modelname)
            return six.text_type(model.objects.get(id=object_id))
        else:
            return self.email

    def _extract_obj(self):
        if len(self.email.split(':')) == 3:
            modelname, object_id, printmodel = self.email.split(':')
            printmodel_obj = PrintModel.objects.get(id=printmodel)
            model = apps.get_model(modelname)
            self.item = model.objects.get(id=object_id)
            if hasattr(self.item, "get_document_filename"):
                pdf_name = "%s.pdf" % self.item.get_document_filename()
            else:
                pdf_name = "%s.pdf" % remove_accent(printmodel_obj.name)
            gen = ReportingGenerator()
            gen.items = self.get_send_email_objects()
            gen.model_text = printmodel_obj.value
            pdf_file = BytesIO(gen.generate_report(None, False))
            self.print_file = [(pdf_name, pdf_file)]
        else:
            self.print_file = None
            self.item = None

    def get_emails(self):
        if not hasattr(self, 'item'):
            self._extract_obj()
        if self.item is not None:
            cclist = self.item.get_email(False)
            return self.item.get_email(True), cclist if len(cclist) > 0 else None
        else:
            return [self.email], None

    def get_attach_files(self):
        if not hasattr(self, 'print_file'):
            self._extract_obj()
        if self.print_file is not None:
            return self.print_file
        else:
            return self.message.attach_files

    def replace_tag(self, text):
        if not hasattr(self, 'item'):
            self._extract_obj()
        contact = None
        doc_reference = ''
        if self.item is not None:
            if hasattr(self.item, 'contact'):
                contact = self.item.contact
            elif isinstance(self.item, AbstractContact):
                contact = self.item
            if hasattr(self.item, 'reference'):
                doc_reference = self.item.reference
            else:
                doc_reference = six.text_type(self.item.id)
        first_doc_name = ''
        if (first_doc_name == '') and (len(self.get_attach_files()) > 0):
            first_doc_name = self.get_attach_files()[0][0]
        if contact is None:
            contact = self.contact
        text = text.replace('#name', contact.get_final_child().get_presentation() if contact is not None else '???')
        text = text.replace('#doc', first_doc_name)
        text = text.replace('#reference', doc_reference)
        return text

    def send_email(self, http_root_address):
        getLogger('lucterios.mailing').debug('EmailSent.send_email(http_root_address=%s)', http_root_address)
        try:
            body = self.replace_tag(self.message.email_content)
            h2txt = HTML2Text()
            h2txt.ignore_links = False
            body_txt = h2txt.handle(body)
            if http_root_address != '':
                self.message.http_root_address = http_root_address
                img_html = "<img src='%s/lucterios.mailing/emailSentAddForStatistic?emailsent=%d' alt=''/>" % (http_root_address, self.id)
                body = body.replace('</body>', img_html + '</body>')
            email, ccemail = self.get_emails()
            getLogger('lucterios.mailing').debug('send email %s : %s' % (self.message.subject, email))
            send_email(email, self.replace_tag(self.message.subject), body, files=self.get_attach_files(), cclist=ccemail, withcopy=self.item is not None, body_txt=body_txt)
            self.success = True
        except Exception as error:
            if getLogger('lucterios.mailing').isEnabledFor(DEBUG):
                getLogger('lucterios.mailing').exception('send_email')
            self.success = False
            self.error = six.text_type(error)
        self.save()

    class Meta(object):
        verbose_name = _('email sent info')
        verbose_name_plural = _('email sent info')
        default_permissions = []
        ordering = ['-last_open_date', 'contact', '-date', 'email']


def send_mailing_in_waiting(http_root_address):
    '''Mailing'''
    msg_list = Message.objects.filter(status=2)
    if len(msg_list) == 0:
        LucteriosScheduler.remove(send_mailing_in_waiting)
    else:
        for msg_item in msg_list:
            msg_item.sendemail(Params.getvalue('mailing-nb-by-batch'), http_root_address)


def add_mailing_in_scheduler(check_nb=True, http_root_address=""):
    if not check_nb or (Message.objects.filter(status=2).count() > 0):
        LucteriosScheduler.add_task(send_mailing_in_waiting, minutes=Params.getvalue('mailing-delay-batch'), http_root_address=http_root_address)


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

    Parameter.check_and_create(name='mailing-dkim-private-path', typeparam=0, title=_("mailing-dkim-private-path"), args="{'Multi': False}", value='')
    Parameter.check_and_create(name='mailing-dkim-selector', typeparam=0, title=_("mailing-dkim-selector"), args="{'Multi': False}", value='default')


@Signal.decorate('auditlog_register')
def mailing_auditlog_register():
    auditlog.register(Message, include_fields=['status', 'date', 'subject', 'body', 'recipients', 'attachments'])
