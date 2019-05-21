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

from email.mime.text import MIMEText
from smtplib import SMTP, SMTP_SSL
from html2text import HTML2Text
from os.path import isfile

from email.utils import formatdate, make_msgid
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication

from django.utils import six
from django.utils.translation import ugettext_lazy as _

from lucterios.CORE.parameters import Params
from lucterios.framework.error import LucteriosException, IMPORTANT
from lucterios.contacts.models import LegalEntity
from logging import getLogger


def will_mail_send():
    sender_email = LegalEntity.objects.get(id=1).email
    return (sender_email != '') and (Params.getvalue('mailing-smtpserver') != '')


def split_doubled_email(email_list):
    if isinstance(email_list, list):
        for email_sep in (";", ","):
            email_list = email_sep.join(email_list).split(email_sep)
        return email_list
    else:
        return None


def send_email(recipients, subject, body, files=None, cclist=None, bcclist=None, withcopy=False, body_txt=None):
    smtp_server = Params.getvalue('mailing-smtpserver')
    sender_obj = LegalEntity.objects.get(id=1)
    sender_name = sender_obj.name
    sender_email = sender_obj.email
    if (sender_email == '') or (smtp_server == ''):
        raise LucteriosException(IMPORTANT, _('Email not configure!'))
    if recipients is None:
        recipients = sender_email
    if not isinstance(recipients, list):
        recipients = [six.text_type(recipients)]
    recipients = split_doubled_email(recipients)
    smtp_port = Params.getvalue('mailing-smtpport')
    smtp_user = Params.getvalue('mailing-smtpuser')
    smtp_pass = Params.getvalue('mailing-smtppass')
    smtp_security = Params.getvalue('mailing-smtpsecurity')
    dkim_private_path = Params.getvalue('mailing-dkim-private-path')
    dkim_selector = Params.getvalue('mailing-dkim-selector')
    msg = MIMEMultipart()
    msg['Date'] = formatdate(localtime=True)
    msg['Subject'] = six.text_type(subject)
    msg['To'] = ", ".join(recipients)
    if isinstance(cclist, list):
        cclist = split_doubled_email(cclist)
        for recipient in recipients:
            if recipient in cclist:
                cclist.remove(recipient)
        msg['Cc'] = ", ".join(cclist)
        recipients.extend(cclist)
    if withcopy:
        if bcclist is None:
            bcclist = []
        if sender_email not in bcclist:
            bcclist.append(sender_email)
    if isinstance(bcclist, list):
        bcclist = split_doubled_email(bcclist)
        for recipient in recipients:
            if recipient in bcclist:
                bcclist.remove(recipient)
        recipients.extend(bcclist)
    domain = sender_email.split('@')[-1]
    msg_from = "%s <%s>" % (sender_name, sender_email)
    msg['From'] = msg_from
    msg['Return-Path'] = sender_email
    msg['Message-ID'] = make_msgid(domain=domain)
    body = six.text_type(body).strip()
    if body[:6].lower() == '<html>':
        if body_txt is None:
            h2txt = HTML2Text()
            h2txt.ignore_links = False
            body_txt = h2txt.handle(body)
        msg_alternative = MIMEMultipart('alternative')
        msg_alternative.attach(MIMEText(body, 'html', 'utf-8'))
        msg_alternative.attach(MIMEText(body_txt, 'plain', 'utf-8'))
        msg.attach(msg_alternative)
    else:
        msg.attach(MIMEText(body, 'plain', 'utf-8'))
    if (files is not None) and (len(files) > 0):
        for filename, file in files:
            msg.attach(MIMEApplication(
                file.read(),
                Content_Disposition='attachment; filename="%s"' % filename,
                Name=filename
            ))
    if (dkim_private_path != '') and isfile(dkim_private_path) and (dkim_selector != ''):
        import dkim
        with open(dkim_private_path) as dkim_private_file:
            privateKey = dkim_private_file.read()
        headers = [b'from', b'to', b'subject']
        sig = dkim.sign(msg.as_string().encode(), dkim_selector.encode(), domain.encode(), privateKey.encode(), include_headers=headers)
        sig = sig.decode()
        msg['DKIM-Signature'] = sig[len("DKIM-Signature: "):]
    server = None
    try:
        if smtp_security == 2:
            server = SMTP_SSL(smtp_server, smtp_port)
        else:
            server = SMTP(smtp_server, smtp_port)
        if smtp_security == 1:
            server.starttls()
        if (smtp_pass != '') and (smtp_user != ''):
            server.login(smtp_user, smtp_pass)
        server.sendmail(msg_from, recipients, msg.as_string())
    except Exception as error:
        raise LucteriosException(IMPORTANT, six.text_type(error))
    finally:
        if server:
            server.quit()


def send_connection_by_email(recipients, alias, passwd):
    subject = _("Connection password")
    message = Params.getvalue('mailing-msg-connection') % {'username': alias, 'password': passwd}
    msg_connection = "<html>"
    msg_connection += message.replace('{[newline]}', '<br/>').replace('{[', '<').replace(']}', '>')
    msg_connection += "</html>"
    send_email(recipients, subject, msg_connection)
