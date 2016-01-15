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
from asyncore import ExitNow
from base64 import b64decode
from os.path import join, dirname
import smtpd
import asyncore
import logging
import email
from _io import BytesIO
from io import SEEK_END

from django.utils import six

from lucterios.framework.test import LucteriosTest
from lucterios.framework.xfergraphic import XferContainerAcknowledge
from lucterios.framework.filetools import get_user_dir
from lucterios.framework.error import LucteriosException
from lucterios.framework.tools import get_binay
from lucterios.CORE.parameters import Params
from lucterios.CORE.models import Parameter
from lucterios.CORE.views_usergroup import UsersEdit

from lucterios.contacts.tests_contacts import change_ourdetail, create_jack
from lucterios.mailing.views import Configuration, SendEmailTry
from lucterios.mailing.functions import will_mail_send, send_email
from lucterios.mailing.views_message import MessageAddModify, MessageList, MessageDel, MessageShow, MessageValidRecipient, MessageDelRecipient, MessageValid,\
    MessageEmail, MessageLetter
from unittest.case import TestCase


def decode_b64(data):
    byte_string = data.encode('utf-8')
    decoded = b64decode(byte_string)
    return decoded.decode('utf-8')


def configSMTP(server, port, security=0, user='', passwd=''):
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

    def check_first_message(self, subject, nb_multi):
        msg = email.message_from_string(self.get(0)[3])
        self.assertTrue(subject in msg.get(
            'Content-Type', ''), msg.get('Content-Type', ''))
        self.assertEqual(nb_multi, len(msg.get_payload()))
        return msg.get_payload()


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

    def test_config(self):
        self.factory.xfer = Configuration()
        self.call('/lucterios.mailing/configuration', {}, False)
        self.assert_observer(
            'core.custom', 'lucterios.mailing', 'configuration')
        self.assert_count_equal('CONTEXT', 0)
        self.assert_count_equal('COMPONENTS/*', 18)
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
        self.assert_xml_equal(
            'COMPONENTS/LABELFORM[@name="mailing-msg-connection"]', 'Confirmation de connexion à votre application:\nAlias:%(username)s\nMot de passe:%(password)s\n')

    def test_tryemail_noconfig(self):
        configSMTP('', 25)
        self.assertEqual(0, self.server.count())
        self.factory.xfer = SendEmailTry()
        self.call('/lucterios.mailing/sendEmailTry', {}, False)
        self.assert_observer(
            'core.exception', 'lucterios.mailing', 'sendEmailTry')
        self.assert_xml_equal(
            "EXCEPTION/MESSAGE", "Mauvais paramètrage du courriel")
        self.assertEqual(0, self.server.count())

    def test_tryemail_success(self):
        configSMTP('localhost', 1025)
        self.assertEqual(0, self.server.count())
        self.factory.xfer = SendEmailTry()
        self.call('/lucterios.mailing/sendEmailTry', {}, False)
        self.assert_observer(
            'core.dialogbox', 'lucterios.mailing', 'sendEmailTry')
        self.assert_xml_equal('TEXT', 'Courriel envoyé, veuillez le vérifier.')
        self.assertEqual(1, self.server.count())
        self.assertEqual(
            'mr-sylvestre@worldcompany.com', self.server.get(0)[1])
        self.assertEqual(
            ['mr-sylvestre@worldcompany.com'], self.server.get(0)[2])
        msg, = self.server.check_first_message('Essai de courriel', 1)
        self.assertEqual('text/plain', msg.get_content_type())
        self.assertEqual(
            'base64', msg.get('Content-Transfer-Encoding', ''))
        self.assertEqual(
            'Courriel envoyé pour vérifier la configuration', decode_b64(msg.get_payload()))

    def test_send_no_config(self):
        configSMTP('', 25)
        self.assertEqual(0, self.server.count())
        self.assertEqual(False, will_mail_send())
        try:
            send_email('toto@machin.com', 'send without config', 'boom!!!')
            self.assertTrue(False)
        except LucteriosException as error:
            self.assertEqual(six.text_type(error), 'Courriel non configuré!')
        self.assertEqual(0, self.server.count())

    def test_send_bad_config(self):
        configSMTP('localhost', 1125)
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
        configSMTP('localhost', 1025)
        self.assertEqual(0, self.server.count())
        self.assertEqual(True, will_mail_send())
        send_email('toto@machin.com', 'send correct config', 'Yessss!!!')
        self.assertEqual(1, self.server.count())
        self.assertEqual(
            'mr-sylvestre@worldcompany.com', self.server.get(0)[1])
        self.assertEqual(['toto@machin.com'], self.server.get(0)[2])
        msg, = self.server.check_first_message('send correct config', 1)
        self.assertEqual('text/plain', msg.get_content_type())
        self.assertEqual('base64', msg.get('Content-Transfer-Encoding', ''))
        self.assertEqual('Yessss!!!', decode_b64(msg.get_payload()))
        self.assertEqual(None, self.server.smtp.auth_params)

    def test_send_html(self):
        configSMTP('localhost', 1025)
        self.assertEqual(0, self.server.count())
        self.assertEqual(True, will_mail_send())
        send_email('toto@machin.com', 'send html',
                   '<html><body><h1>Yessss!!!</h1></body></html>')
        self.assertEqual(1, self.server.count())
        self.assertEqual(
            'mr-sylvestre@worldcompany.com', self.server.get(0)[1])
        self.assertEqual(['toto@machin.com'], self.server.get(0)[2])
        msg, = self.server.check_first_message('send html', 1)
        self.assertEqual('text/html', msg.get_content_type())
        self.assertEqual('base64', msg.get('Content-Transfer-Encoding', ''))
        self.assertEqual(
            '<html><body><h1>Yessss!!!</h1></body></html>', decode_b64(msg.get_payload()))

    def test_send_with_auth(self):
        if six.PY3:
            self.server.smtp.with_authentificate = True
            configSMTP('localhost', 1025, 0, 'toto', 'abc123')
            self.assertEqual(0, self.server.count())
            self.assertEqual(True, will_mail_send())
            send_email('toto@machin.com', 'send with auth', 'OK!')
            self.assertEqual(1, self.server.count())
            msg, = self.server.check_first_message('send with auth', 1)
            self.assertEqual('OK!', decode_b64(msg.get_payload()))
            self.assertEqual(
                ['', 'toto', 'abc123'], self.server.smtp.auth_params)

    def test_send_with_starttls(self):
        configSMTP('localhost', 1025, 1)
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
        configSMTP('localhost', 1025, 2)
        self.assertEqual(0, self.server.count())
        self.assertEqual(True, will_mail_send())
        try:
            send_email('toto@machin.com', 'send with ssl', 'not success!')
            self.assertTrue(False)
        except LucteriosException as error:
            self.assertTrue(
                'unknown protocol' in six.text_type(error), six.text_type(error))
        self.assertEqual(0, self.server.count())

    def test_send_with_files(self):
        file1 = BytesIO(get_binay('blablabla\blabla.'))
        file2 = open(
            join(dirname(__file__), 'static', 'lucterios.mailing', 'images', 'config_mail.png'), mode='rb')
        try:
            configSMTP('localhost', 1025)
            self.assertEqual(0, self.server.count())
            self.assertEqual(True, will_mail_send())
            send_email('toto@machin.com', 'send with files', '2 files sent!',
                       [('filename1.txt', file1), ('filename2.png', file2)])
            self.assertEqual(1, self.server.count())
            self.assertEqual(
                'mr-sylvestre@worldcompany.com', self.server.get(0)[1])
            self.assertEqual(['toto@machin.com'], self.server.get(0)[2])
            msg, msg_f1, msg_f2 = self.server.check_first_message(
                'send with files', 3)
            self.assertEqual('text/plain', msg.get_content_type())
            self.assertEqual(
                'base64', msg.get('Content-Transfer-Encoding', ''))
            self.assertEqual('2 files sent!', decode_b64(msg.get_payload()))
            self.assertEqual(None, self.server.smtp.auth_params)
            self.assertTrue('filename1.txt' in msg_f1.get(
                'Content-Type', ''), msg_f1.get('Content-Type', ''))
            self.assertEqual(
                'blablabla\blabla.', decode_b64(msg_f1.get_payload()))
            self.assertTrue('filename2.png' in msg_f2.get(
                'Content-Type', ''), msg_f2.get('Content-Type', ''))
            file2.seek(0, SEEK_END)
            self.assertEqual(
                file2.tell(), len(b64decode(msg_f2.get_payload())))
        finally:
            file1.close()
            file2.close()

    def test_user_withoutconfig(self):
        configSMTP('', 25)
        self.factory.xfer = UsersEdit()
        self.call('/CORE/usersEdit', {}, False)
        self.assert_observer('core.custom', 'CORE', 'usersEdit')
        self.assert_count_equal('COMPONENTS/*', 39)

    def test_user_withconfig(self):
        configSMTP('localhost', 1025)
        self.factory.xfer = UsersEdit()
        self.call('/CORE/usersEdit', {}, False)
        self.assert_observer('core.custom', 'CORE', 'usersEdit')
        self.assert_count_equal('COMPONENTS/*', 41)
        self.assert_xml_equal(
            'COMPONENTS/LABELFORM[@name="lbl_password_generate"]', "{[b]}Générer un nouveau mot de passe?{[/b]}")

    def test_user_change_password(self):
        configSMTP('localhost', 1025)
        self.assertEqual(0, self.server.count())
        self.factory.xfer = UsersEdit()
        self.call('/CORE/usersEdit', {'SAVE': 'YES', 'user_actif': '1',
                                      "password_generate": 'o', "email": 'admin@super.com'}, False)
        self.assert_observer('core.acknowledge', 'CORE', 'usersEdit')
        self.assertEqual(1, self.server.count())
        msg, = self.server.check_first_message('Mot de passe de connexion', 1)
        self.assertEqual('text/plain', msg.get_content_type())
        self.assertEqual('base64', msg.get('Content-Transfer-Encoding', ''))
        self.assertEqual(
            'Confirmation de connexion à votre application:\nAlias:admin\nMot de passe:', decode_b64(msg.get_payload())[:72])


class MailingTest(LucteriosTest):

    def setUp(self):
        self.xfer_class = XferContainerAcknowledge
        LucteriosTest.setUp(self)
        change_ourdetail()
        create_jack()

    def test_messages(self):
        self.factory.xfer = MessageList()
        self.call('/lucterios.mailing/messageList', {}, False)
        self.assert_observer('core.custom', 'lucterios.mailing', 'messageList')
        self.assert_count_equal('COMPONENTS/GRID[@name="message"]/RECORD', 0)

        self.factory.xfer = MessageAddModify()
        self.call('/lucterios.mailing/messageAddModify', {}, False)
        self.assert_observer(
            'core.custom', 'lucterios.mailing', 'messageAddModify')
        self.assert_count_equal('COMPONENTS/*', 5)

        self.factory.xfer = MessageAddModify()
        self.call('/lucterios.mailing/messageAddModify', {'SAVE': 'YES', 'subject': 'new message', 'body':
                                                          '{[b]}{[font color="blue"]}All{[/font]}{[/b]}{[newline]}Small message to give a big {[u]}kiss{[/u]} ;){[newline]}{[newline]}Bye'}, False)
        self.assert_observer(
            'core.acknowledge', 'lucterios.mailing', 'messageAddModify')

        self.factory.xfer = MessageList()
        self.call('/lucterios.mailing/messageList', {}, False)
        self.assert_observer('core.custom', 'lucterios.mailing', 'messageList')
        self.assert_count_equal('COMPONENTS/GRID[@name="message"]/RECORD', 1)
        self.assert_xml_equal(
            'COMPONENTS/GRID[@name="message"]/RECORD[1]/VALUE[@name="status"]', "ouvert")
        self.assert_xml_equal(
            'COMPONENTS/GRID[@name="message"]/RECORD[1]/VALUE[@name="date"]', '---')
        self.assert_xml_equal(
            'COMPONENTS/GRID[@name="message"]/RECORD[1]/VALUE[@name="subject"]', 'new message')

        self.factory.xfer = MessageDel()
        self.call('/lucterios.mailing/messageDel',
                  {'message': '1', 'CONFIRME': 'YES'}, False)
        self.assert_observer(
            'core.acknowledge', 'lucterios.mailing', 'messageDel')

        self.factory.xfer = MessageList()
        self.call('/lucterios.mailing/messageList', {}, False)
        self.assert_observer('core.custom', 'lucterios.mailing', 'messageList')
        self.assert_count_equal('COMPONENTS/GRID[@name="message"]/RECORD', 0)

    def test_show_message(self):
        self.factory.xfer = MessageAddModify()
        self.call('/lucterios.mailing/messageAddModify', {'SAVE': 'YES', 'subject': 'new message', 'body':
                                                          '{[b]}{[font color="blue"]}All{[/font]}{[/b]}{[newline]}Small message to give a big {[u]}kiss{[/u]} ;){[newline]}{[newline]}Bye'}, False)
        self.assert_observer(
            'core.acknowledge', 'lucterios.mailing', 'messageAddModify')

        self.factory.xfer = MessageShow()
        self.call('/lucterios.mailing/messageShow', {'message': '1'}, False)
        self.assert_observer('core.custom', 'lucterios.mailing', 'messageShow')
        self.assert_count_equal('COMPONENTS/*', 12)
        self.assert_count_equal('ACTIONS/ACTION', 2)
        self.assert_action_equal(
            'ACTIONS/ACTION[1]', ('Modifier', 'images/edit.png', 'lucterios.mailing', 'messageAddModify', 1, 1, 1))
        self.assert_action_equal(
            'ACTIONS/ACTION[2]', ('Fermer', 'images/close.png'))
        self.assert_count_equal(
            'COMPONENTS/GRID[@name="recipient_list"]/RECORD', 0)

        self.factory.xfer = MessageValidRecipient()
        self.call('/lucterios.mailing/messageValidRecipient',
                  {'message': '1', 'modelname': 'contacts.Individual', 'CRITERIA': 'genre||8||1'}, False)
        self.assert_observer(
            'core.acknowledge', 'lucterios.mailing', 'messageValidRecipient')
        self.factory.xfer = MessageValidRecipient()
        self.call('/lucterios.mailing/messageValidRecipient',
                  {'message': '1', 'modelname': 'contacts.AbstractContact', 'CRITERIA': ''}, False)
        self.assert_observer(
            'core.acknowledge', 'lucterios.mailing', 'messageValidRecipient')
        self.factory.xfer = MessageValidRecipient()
        self.call('/lucterios.mailing/messageValidRecipient',
                  {'message': '1', 'modelname': 'contacts.LegalEntity', 'CRITERIA': 'name||5||truc'}, False)
        self.assert_observer(
            'core.acknowledge', 'lucterios.mailing', 'messageValidRecipient')

        self.factory.xfer = MessageShow()
        self.call('/lucterios.mailing/messageShow', {'message': '1'}, False)
        self.assert_observer('core.custom', 'lucterios.mailing', 'messageShow')
        self.assert_count_equal('COMPONENTS/*', 13)
        self.assert_count_equal('ACTIONS/ACTION', 3)
        self.assert_action_equal(
            'ACTIONS/ACTION[1]', ('Valider', 'images/ok.png', 'lucterios.mailing', 'messageValid', 0, 1, 1))
        self.assert_action_equal(
            'ACTIONS/ACTION[2]', ('Modifier', 'images/edit.png', 'lucterios.mailing', 'messageAddModify', 1, 1, 1))
        self.assert_action_equal(
            'ACTIONS/ACTION[3]', ('Fermer', 'images/close.png'))
        self.assert_xml_equal(
            'COMPONENTS/LABELFORM[@name="status"]', 'ouvert')
        self.assert_count_equal(
            'COMPONENTS/GRID[@name="recipient_list"]/ACTIONS/ACTION', 2)
        self.assert_count_equal(
            'COMPONENTS/GRID[@name="recipient_list"]/RECORD', 3)
        self.assert_xml_equal(
            'COMPONENTS/GRID[@name="recipient_list"]/RECORD[1]/VALUE[@name="model"]', "Personne Physique")
        self.assert_xml_equal(
            'COMPONENTS/GRID[@name="recipient_list"]/RECORD[1]/VALUE[@name="filter"]', '{[b]}genre{[/b]} égal {[i]}"Homme"{[/i]}')
        self.assert_xml_equal(
            'COMPONENTS/GRID[@name="recipient_list"]/RECORD[2]/VALUE[@name="model"]', "Contact Générique")
        self.assert_xml_equal(
            'COMPONENTS/GRID[@name="recipient_list"]/RECORD[3]/VALUE[@name="model"]', "Personne Morale")

        self.factory.xfer = MessageDelRecipient()
        self.call('/lucterios.mailing/messageDelRecipient',
                  {'message': '1', 'recipient_list': '1', 'CONFIRME': 'YES'}, False)
        self.assert_observer(
            'core.acknowledge', 'lucterios.mailing', 'messageDelRecipient')

        self.factory.xfer = MessageShow()
        self.call('/lucterios.mailing/messageShow', {'message': '1'}, False)
        self.assert_observer('core.custom', 'lucterios.mailing', 'messageShow')
        self.assert_count_equal('COMPONENTS/*', 13)
        self.assert_count_equal(
            'COMPONENTS/GRID[@name="recipient_list"]/RECORD', 2)

    def test_validate_message(self):
        configSMTP('', 25)
        self.factory.xfer = MessageAddModify()
        self.call('/lucterios.mailing/messageAddModify', {'SAVE': 'YES', 'subject': 'new message', 'body':
                                                          '{[b]}{[font color="blue"]}All{[/font]}{[/b]}{[newline]}Small message to give a big {[u]}kiss{[/u]} ;){[newline]}{[newline]}Bye'}, False)
        self.factory.xfer = MessageValidRecipient()
        self.call('/lucterios.mailing/messageValidRecipient',
                  {'message': '1', 'modelname': 'contacts.Individual', 'CRITERIA': 'genre||8||1'}, False)
        self.factory.xfer = MessageValidRecipient()
        self.call('/lucterios.mailing/messageValidRecipient',
                  {'message': '1', 'modelname': 'contacts.LegalEntity', 'CRITERIA': ''}, False)
        self.factory.xfer = MessageValid()
        self.call('/lucterios.mailing/messageValid',
                  {'message': '1', 'CONFIRME': 'YES'}, False)
        self.assert_observer(
            'core.acknowledge', 'lucterios.mailing', 'messageValid')

        self.factory.xfer = MessageShow()
        self.call('/lucterios.mailing/messageShow', {'message': '1'}, False)
        self.assert_observer('core.custom', 'lucterios.mailing', 'messageShow')
        self.assert_count_equal('COMPONENTS/*', 13)
        self.assert_xml_equal('COMPONENTS/LABELFORM[@name="status"]', 'fermé')
        self.assert_count_equal(
            'COMPONENTS/GRID[@name="recipient_list"]/ACTIONS/ACTION', 0)
        self.assert_count_equal(
            'COMPONENTS/GRID[@name="recipient_list"]/RECORD', 2)
        self.assert_xml_equal(
            'COMPONENTS/LABELFORM[@name="contact_nb"]', 'Message défini pour 2 contacts')
        self.assert_count_equal('ACTIONS/ACTION', 2)
        self.assert_action_equal(
            'ACTIONS/ACTION[1]', ('Lettres', 'lucterios.mailing/images/letter.png', 'lucterios.mailing', 'messageLetter', 0, 1, 1))
        self.assert_action_equal(
            'ACTIONS/ACTION[2]', ('Fermer', 'images/close.png'))

        configSMTP('localhost', 1025)
        self.factory.xfer = MessageShow()
        self.call('/lucterios.mailing/messageShow', {'message': '1'}, False)
        self.assert_observer('core.custom', 'lucterios.mailing', 'messageShow')
        self.assert_count_equal('ACTIONS/ACTION', 3)
        self.assert_action_equal(
            'ACTIONS/ACTION[1]', ('Lettres', 'lucterios.mailing/images/letter.png', 'lucterios.mailing', 'messageLetter', 0, 1, 1))
        self.assert_action_equal(
            'ACTIONS/ACTION[2]', ('Courriels', 'lucterios.mailing/images/email.png', 'lucterios.mailing', 'messageEmail', 0, 1, 1))
        self.assert_action_equal(
            'ACTIONS/ACTION[3]', ('Fermer', 'images/close.png'))

    def test_email_message(self):
        configSMTP('localhost', 1025)
        self.factory.xfer = MessageAddModify()
        self.call('/lucterios.mailing/messageAddModify', {'SAVE': 'YES', 'subject': 'new message', 'body':
                                                          '{[b]}{[font color="blue"]}All{[/font]}{[/b]}{[newline]}Small message to give a big {[u]}kiss{[/u]} ;){[newline]}{[newline]}Bye'}, False)
        self.factory.xfer = MessageValidRecipient()
        self.call('/lucterios.mailing/messageValidRecipient',
                  {'message': '1', 'modelname': 'contacts.Individual', 'CRITERIA': 'genre||8||1'}, False)
        self.factory.xfer = MessageValidRecipient()
        self.call('/lucterios.mailing/messageValidRecipient',
                  {'message': '1', 'modelname': 'contacts.LegalEntity', 'CRITERIA': ''}, False)
        self.factory.xfer = MessageValid()
        self.call('/lucterios.mailing/messageValid',
                  {'message': '1', 'CONFIRME': 'YES'}, False)
        server = TestReceiver()
        server.start(1025)
        try:
            self.assertEqual(0, server.count())
            self.factory.xfer = MessageEmail()
            self.call('/lucterios.mailing/messageEmail',
                      {'message': '1', 'CONFIRME': 'YES'}, False)
            self.assert_observer(
                'core.dialogbox', 'lucterios.mailing', 'messageEmail')
            self.assertEqual(2, server.count())
            self.assertEqual(
                'mr-sylvestre@worldcompany.com', server.get(0)[1])
            self.assertEqual(
                ['mr-sylvestre@worldcompany.com'], server.get(0)[2])
            msg, = server.check_first_message('new message', 1)
            self.assertEqual('text/html', msg.get_content_type())
            self.assertEqual(
                'base64', msg.get('Content-Transfer-Encoding', ''))
            self.assertEqual(
                '<html><body><b><font color="blue">All</font></b><br/>Small message to give a big <u>kiss</u> ;)<br/><br/>Bye</body></html>', decode_b64(msg.get_payload()))
        finally:
            server.stop()

    def test_letter_message(self):
        self.factory.xfer = MessageAddModify()
        self.call('/lucterios.mailing/messageAddModify', {'SAVE': 'YES', 'subject': 'new message', 'body':
                                                          '{[b]}{[font color="blue"]}All{[/font]}{[/b]}{[newline]}Small message to give a big {[u]}kiss{[/u]} ;){[newline]}{[newline]}Bye'}, False)
        self.factory.xfer = MessageValidRecipient()
        self.call('/lucterios.mailing/messageValidRecipient',
                  {'message': '1', 'modelname': 'contacts.Individual', 'CRITERIA': 'genre||8||1'}, False)
        self.factory.xfer = MessageValidRecipient()
        self.call('/lucterios.mailing/messageValidRecipient',
                  {'message': '1', 'modelname': 'contacts.LegalEntity', 'CRITERIA': ''}, False)
        self.factory.xfer = MessageValid()
        self.call('/lucterios.mailing/messageValid',
                  {'message': '1', 'CONFIRME': 'YES'}, False)

        self.factory.xfer = MessageLetter()
        self.call('/lucterios.mailing/messageLetter',
                  {'message': '1', 'PRINT_MODE': '3', 'MODEL': 5}, False)
        self.assert_observer(
            'core.print', 'lucterios.mailing', 'messageLetter')
        pdf_value = b64decode(
            six.text_type(self.get_first_xpath('PRINT').text))
        self.assertEqual(pdf_value[:4], "%PDF".encode('ascii', 'ignore'))
