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
from asyncore import ExitNow
from base64 import b64decode
from threading import Thread
from os.path import isfile
from os import remove
import asyncore
import smtpd
import logging
import email

from django.test.testcases import TestCase

from lucterios.CORE.parameters import Params


def decode_b64(data):
    byte_string = data.encode('utf-8')
    decoded = b64decode(byte_string)
    return decoded.decode('utf-8')


def configSMTP(server, port, security=0, user='', passwd='', batchtime=0.1, batchsize=20, dkim_private_file=''):
    Params.setvalue(name='mailing-smtpserver', value=server)
    Params.setvalue(name='mailing-smtpport', value=port)
    Params.setvalue(name='mailing-smtpsecurity', value=security)
    Params.setvalue(name='mailing-smtpuser', value=user)
    Params.setvalue(name='mailing-smtppass', value=passwd)
    Params.setvalue(name='mailing-dkim-private-path', value=dkim_private_file)
    Params.setvalue(name='mailing-delay-batch', value="%.1f" % batchtime)
    Params.setvalue(name='mailing-nb-by-batch', value="%.d" % batchsize)


def configSMS(file_name='/tmp/sms.txt', max_sms=3):
    Params.setvalue('mailing-sms-provider', 'TestProvider')
    Params.setvalue('mailing-sms-option', 'file name = %s{[br/]}max = %d' % (file_name, max_sms))


def clean_sms_testfile(create_new, file_name='/tmp/sms.txt'):
    if isfile(file_name):
        remove(file_name)
    if create_new:
        with open(file_name, "w"):
            pass


def read_sms(file_name='/tmp/sms.txt'):
    if isfile(file_name):
        with open(file_name, 'r') as sms_file:
            sms_content = sms_file.readlines()
        return sms_content
    else:
        return None


class TestSMTPChannel(smtpd.SMTPChannel):

    def smtp_AUTH(self, arg):
        if 'PLAIN' in arg:
            split_args = arg.split(' ')
            self.smtp_server.auth_params = decode_b64(
                split_args[1]).split('\0')
            logging.getLogger("lucterios.mailing.test").info(
                "smtp_AUTH %s", self.smtp_server.auth_params)
            self.push('235 Authentication successful.')
        else:
            self.push('454 Temporary authentication failure.')
            raise ExitNow()

    def smtp_EHLO(self, arg):
        if self.smtp_server.with_authentificate:
            if not arg:
                self.push('501 Syntax: EHLO hostname')
                return
            if self.seen_greeting:
                self.push('503 Duplicate HELO/EHLO')
            else:
                self.seen_greeting = arg
                self.extended_smtp = True
                self.push('250-%s Hello %s' % (self.fqdn, arg))
                self.push('250-AUTH LOGIN PLAIN')
                self.push('250 EHLO')
        else:
            smtpd.SMTPChannel.smtp_EHLO(self, arg)

    def smtp_RCPT(self, arg):
        if self.smtp_server.wrong_email is not None:
            import re
            address = re.findall(r"^TO:<(.*)>$", arg)
            if len(address) == 0:
                self.push('501 Syntax: RCPT TO: <address>')
                return
            if self.smtp_server.wrong_email in address:
                self.push('550 Bad <address> : %s' % self.smtp_server.wrong_email)
                return
        smtpd.SMTPChannel.smtp_RCPT(self, arg)


class TestSMTPServer(smtpd.SMTPServer):
    channel_class = TestSMTPChannel
    emails = []
    with_authentificate = False
    auth_params = None
    wrong_email = None

    def process_message(self, peer, mailfrom, rcpttos, data, **kwargs):
        self.emails.append((peer, mailfrom, rcpttos, data))
        logging.getLogger("lucterios.mailing.test").info("email %s => %s", mailfrom, rcpttos)


class TestReceiver(TestCase):

    def __init__(self):
        TestCase.__init__(self, methodName='stop')

    def start(self, port):
        self.smtp = TestSMTPServer(('0.0.0.0', port), None)
        self.smtp.emails = []
        self.smtp.with_authentificate = False
        self.smtp.auth_params = None
        self.smtp.wrong_email = None
        self.thread = Thread(target=asyncore.loop, kwargs={'timeout': 1})
        self.thread.start()

    def stop(self):
        self.smtp.close()
        self.thread.join()

    def count(self):
        return len(self.smtp.emails)

    def get(self, index):
        return self.smtp.emails[index]

    def email_list(self):
        return [email[2] for email in self.smtp.emails]

    def get_first_msg(self):
        data = self.get(0)[3]
        if hasattr(data, 'decode'):
            data = data.decode()
        msg = email.message_from_string(data)
        return msg

    def convert_message(self, msg_list):
        msg_result = []
        for msg_item in msg_list:
            if (msg_item.get_content_type() == 'multipart/alternative'):
                msg_result.extend(msg_item.get_payload())
            else:
                msg_result.append(msg_item)
        return msg_result

    def get_msg_index(self, index, subject=None, params=None):
        data = self.get(index)[3]
        if hasattr(data, 'decode'):
            data = data.decode()
        msg = email.message_from_string(data)
        if params is None:
            params = {}
        if isinstance(params, dict):
            if subject is not None:
                params['Subject'] = subject
            for key, val in params.items():
                self.assertEqual(val, msg.get(key, ''), msg.get(key, ''))
        return self.convert_message(msg.get_payload())

    def check_first_message(self, subject, nb_multi, params=None):
        msg_result = self.get_msg_index(0, subject, params)
        self.assertEqual(nb_multi, len(msg_result))
        return msg_result
