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
import asyncore
import smtpd
import logging
import email

from lucterios.CORE.parameters import Params
from lucterios.CORE.models import Parameter
from django.test.testcases import TestCase


def decode_b64(data):
    byte_string = data.encode('utf-8')
    decoded = b64decode(byte_string)
    return decoded.decode('utf-8')


def configSMTP(server, port, security=0, user='', passwd='', batchtime=0.1, batchsize=20, dkim_private_file=''):
    param = Parameter.objects.get(name='mailing-smtpserver')
    param.value = server
    param.save()
    param = Parameter.objects.get(name='mailing-smtpport')
    param.value = port
    param.save()
    param = Parameter.objects.get(name='mailing-smtpsecurity')
    param.value = security
    param.save()
    param = Parameter.objects.get(name='mailing-smtpuser')
    param.value = user
    param.save()
    param = Parameter.objects.get(name='mailing-smtppass')
    param.value = passwd
    param.save()
    param = Parameter.objects.get(name='mailing-dkim-private-path')
    param.value = dkim_private_file
    param.save()
    param = Parameter.objects.get(name='mailing-delay-batch')
    param.value = "%.1f" % batchtime
    param.save()
    param = Parameter.objects.get(name='mailing-nb-by-batch')
    param.value = "%.d" % batchsize
    param.save()
    Params.clear()


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


class TestSMTPServer(smtpd.SMTPServer):
    channel_class = TestSMTPChannel
    emails = []
    with_authentificate = False
    auth_params = None

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
        self.thread = Thread(target=asyncore.loop, kwargs={'timeout': 1})
        self.thread.start()

    def stop(self):
        self.smtp.close()
        self.thread.join()

    def count(self):
        return len(self.smtp.emails)

    def get(self, index):
        return self.smtp.emails[index]

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

    def get_msg_index(self, index, subject=None):
        data = self.get(index)[3]
        if hasattr(data, 'decode'):
            data = data.decode()
        msg = email.message_from_string(data)
        if subject is not None:
            self.assertEqual(subject, msg.get('Subject', ''))
        return self.convert_message(msg.get_payload())

    def check_first_message(self, subject, nb_multi, params=None):
        msg = self.get_first_msg()
        if params is None:
            params = {}
        if isinstance(params, dict):
            params['Subject'] = subject
            for key, val in params.items():
                self.assertEqual(val, msg.get(key, ''), msg.get(key, ''))
        msg_result = self.convert_message(msg.get_payload())
        self.assertEqual(nb_multi, len(msg_result))
        return msg_result
