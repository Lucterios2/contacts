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
from shutil import rmtree
from threading import Thread
from base64 import b64decode
import smtpd
import asyncore
import logging
import email

from django.utils import six

from lucterios.framework.test import LucteriosTest
from lucterios.framework.xfergraphic import XferContainerAcknowledge
from lucterios.framework.filetools import get_user_dir
from lucterios.framework.error import LucteriosException

from lucterios.mailing.views import Configuration, SendEmailTry
from lucterios.mailing.functions import will_mail_send, send_email
from lucterios.CORE.parameters import Params
from lucterios.CORE.models import Parameter
from lucterios.contacts.tests_contacts import change_ourdetail
from asyncore import ExitNow


def decode_b64(data):
    byte_string = data.encode('utf-8')
    decoded = b64decode(byte_string)
    return decoded.decode('utf-8')


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

    def process_message(self, peer, mailfrom, rcpttos, data):
        self.emails.append((peer, mailfrom, rcpttos, data))
        logging.getLogger("lucterios.mailing.test").info(
            "email %s => %s", mailfrom, rcpttos)


class TestReceiver(object):

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


class ConfigurationTest(LucteriosTest):

    def __init__(self, methodName):
        LucteriosTest.__init__(self, methodName)
        self.server = TestReceiver()

    def setUp(self):
        self.xfer_class = XferContainerAcknowledge
        change_ourdetail()
        LucteriosTest.setUp(self)
        rmtree(get_user_dir(), True)
        self.server.start(1025)

    def tearDown(self):
        self.server.stop()
        LucteriosTest.tearDown(self)

    def config(self, server, port, security=0, user='', passwd=''):
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
        Params.clear()

    def test_config(self):
        self.factory.xfer = Configuration()
        self.call('/lucterios.mailing/configuration', {}, False)
        self.assert_observer(
            'Core.Custom', 'lucterios.mailing', 'configuration')
        self.assert_count_equal('CONTEXT', 0)
        self.assert_count_equal('COMPONENTS/*', 13)
        self.assert_xml_equal(
            'COMPONENTS/LABELFORM[@name="mailing-smtpserver"]', None)
        self.assert_xml_equal(
            'COMPONENTS/LABELFORM[@name="mailing-smtpport"]', '25')
        self.assert_xml_equal(
            'COMPONENTS/LABELFORM[@name="mailing-smtpsecurity"]', 'Aucune')
        self.assert_xml_equal(
            'COMPONENTS/LABELFORM[@name="mailing-smtpuser"]', None)
        self.assert_xml_equal(
            'COMPONENTS/LABELFORM[@name="mailing-smtppass"]', None)

    def test_tryemail_noconfig(self):
        self.config('', 25)
        self.assertEqual(0, self.server.count())
        self.factory.xfer = SendEmailTry()
        self.call('/lucterios.mailing/sendEmailTry', {}, False)
        self.assert_observer(
            'CORE.Exception', 'lucterios.mailing', 'sendEmailTry')
        self.assert_xml_equal(
            "EXCEPTION/MESSAGE", "Mauvais paramètrage du courriel")
        self.assertEqual(0, self.server.count())

    def test_tryemail_success(self):
        self.config('localhost', 1025)
        self.assertEqual(0, self.server.count())
        self.factory.xfer = SendEmailTry()
        self.call('/lucterios.mailing/sendEmailTry', {}, False)
        self.assert_observer(
            'Core.DialogBox', 'lucterios.mailing', 'sendEmailTry')
        self.assert_xml_equal('TEXT', 'Courriel envoyé, veuillez verifier.')
        self.assertEqual(1, self.server.count())
        self.assertEqual(
            'mr-sylvestre@worldcompany.com', self.server.get(0)[1])
        self.assertEqual(
            ['mr-sylvestre@worldcompany.com'], self.server.get(0)[2])
        msg = email.message_from_string(self.server.get(0)[3])
        self.assertEqual('Essai de courriel', msg.get('Subject', ''))
        self.assertEqual('text/plain', msg.get_content_type())
        self.assertEqual('base64', msg.get('Content-Transfer-Encoding', ''))
        self.assertEqual(
            'Courriel envoyé pour vérifier la configuration', decode_b64(msg.get_payload()))

    def test_send_no_config(self):
        self.config('', 25)
        self.assertEqual(0, self.server.count())
        self.assertEqual(False, will_mail_send())
        try:
            send_email('toto@machin.com', 'send without config', 'boom!!!')
            self.assertTrue(False)
        except LucteriosException as error:
            self.assertEqual(six.text_type(error), 'Courriel non configuré!')
        self.assertEqual(0, self.server.count())

    def test_send_bad_config(self):
        self.config('localhost', 1125)
        self.assertEqual(0, self.server.count())
        self.assertEqual(True, will_mail_send())
        try:
            send_email('toto@machin.com', 'send without config', 'boom!!!')
            self.assertTrue(False)
        except LucteriosException as error:
            self.assertEqual(
                six.text_type(error), '[Errno 111] Connection refused')
        self.assertEqual(0, self.server.count())

    def test_send_ok(self):
        self.config('localhost', 1025)
        self.assertEqual(0, self.server.count())
        self.assertEqual(True, will_mail_send())
        send_email('toto@machin.com', 'send correct config', 'Yessss!!!')
        self.assertEqual(1, self.server.count())
        self.assertEqual(
            'mr-sylvestre@worldcompany.com', self.server.get(0)[1])
        self.assertEqual(['toto@machin.com'], self.server.get(0)[2])
        msg = email.message_from_string(self.server.get(0)[3])
        self.assertEqual('send correct config', msg.get('Subject', ''))
        self.assertEqual('text/plain', msg.get_content_type())
        self.assertEqual('base64', msg.get('Content-Transfer-Encoding', ''))
        self.assertEqual('Yessss!!!', decode_b64(msg.get_payload()))
        self.assertEqual(None, self.server.smtp.auth_params)

    def test_send_html(self):
        self.config('localhost', 1025)
        self.assertEqual(0, self.server.count())
        self.assertEqual(True, will_mail_send())
        send_email('toto@machin.com', 'send html',
                   '<html><body><h1>Yessss!!!</h1></body><html>')
        self.assertEqual(1, self.server.count())
        self.assertEqual(
            'mr-sylvestre@worldcompany.com', self.server.get(0)[1])
        self.assertEqual(['toto@machin.com'], self.server.get(0)[2])
        msg = email.message_from_string(self.server.get(0)[3])
        self.assertEqual('send html', msg.get('Subject', ''))
        self.assertEqual('text/html', msg.get_content_type())
        self.assertEqual('base64', msg.get('Content-Transfer-Encoding', ''))
        self.assertEqual(
            '<html><body><h1>Yessss!!!</h1></body><html>', decode_b64(msg.get_payload()))

    def test_send_with_auth(self):
        if six.PY3:
            self.server.smtp.with_authentificate = True
            self.config('localhost', 1025, 0, 'toto', 'abc123')
            self.assertEqual(0, self.server.count())
            self.assertEqual(True, will_mail_send())
            send_email('toto@machin.com', 'send with auth', 'OK!')
            self.assertEqual(1, self.server.count())
            msg = email.message_from_string(self.server.get(0)[3])
            self.assertEqual('send with auth', msg.get('Subject', ''))
            self.assertEqual('OK!', decode_b64(msg.get_payload()))
            self.assertEqual(
                ['', 'toto', 'abc123'], self.server.smtp.auth_params)

    def test_send_with_starttls(self):
        self.config('localhost', 1025, 1)
        self.assertEqual(0, self.server.count())
        self.assertEqual(True, will_mail_send())
        try:
            send_email('toto@machin.com', 'send with starttls', 'failed!')
            self.assertTrue(False)
        except LucteriosException as error:
            self.assertEqual(
                six.text_type(error), 'STARTTLS extension not supported by server.')
        self.assertEqual(0, self.server.count())

    def test_send_with_ssl(self):
        self.config('localhost', 1025, 2)
        self.assertEqual(0, self.server.count())
        self.assertEqual(True, will_mail_send())
        try:
            send_email('toto@machin.com', 'send with ssl', 'not success!')
            self.assertTrue(False)
        except LucteriosException as error:
            self.assertTrue(
                'unknown protocol' in six.text_type(error), six.text_type(error))
        self.assertEqual(0, self.server.count())
