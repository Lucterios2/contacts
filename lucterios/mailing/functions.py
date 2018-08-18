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

from email.utils import formatdate
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication

from django.utils import six
from django.utils.translation import ugettext_lazy as _

from lucterios.CORE.parameters import Params
from lucterios.framework.error import LucteriosException, IMPORTANT
from lucterios.contacts.models import LegalEntity


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


def send_email(recipients, subject, body, files=None, cclist=None, bcclist=None, withcopy=False):
    smtp_server = Params.getvalue('mailing-smtpserver')
    sender_email = LegalEntity.objects.get(id=1).email
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
    body = six.text_type(body).strip()
    if body[:6].lower() == '<html>':
        subtype = 'html'
    else:
        subtype = 'plain'
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
    msg['From'] = sender_email
    msg.attach(MIMEText(body, subtype, 'utf-8'))
    if files:
        for filename, file in files:
            msg.attach(MIMEApplication(
                file.read(),
                Content_Disposition='attachment; filename="%s"' % filename,
                Name=filename
            ))
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
        server.sendmail(sender_email, recipients, msg.as_string())
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
