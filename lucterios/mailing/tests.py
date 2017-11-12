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
from base64 import b64decode
from os.path import join, dirname
from _io import BytesIO
from io import SEEK_END

from django.utils import six

from lucterios.framework.test import LucteriosTest
from lucterios.framework.xfergraphic import XferContainerAcknowledge
from lucterios.framework.filetools import get_user_dir
from lucterios.framework.error import LucteriosException
from lucterios.framework.tools import get_binay
from lucterios.CORE.parameters import Params
from lucterios.CORE.models import Parameter, LucteriosUser
from lucterios.CORE.views_usergroup import UsersEdit

from lucterios.contacts.tests_contacts import change_ourdetail, create_jack
from lucterios.mailing.views import Configuration, SendEmailTry
from lucterios.mailing.functions import will_mail_send, send_email
from lucterios.mailing.views_message import MessageAddModify, MessageList, MessageDel, MessageShow, MessageValidRecipient,\
    MessageDelRecipient, MessageEmail, MessageLetter, MessageTransition
from lucterios.CORE.views import AskPassword, AskPasswordAct
from django.contrib.auth.models import AnonymousUser
from lucterios.contacts.views import CreateAccount
from lucterios.contacts.models import Individual, LegalEntity
from lucterios.mailing.test_tools import configSMTP, decode_b64, TestReceiver


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
        self.assert_count_equal('COMPONENTS/*', 2 + 6 + 2 + 2)
        self.assert_xml_equal('COMPONENTS/LABELFORM[@name="mailing-smtpserver"]', None)
        self.assert_xml_equal('COMPONENTS/LABELFORM[@name="mailing-smtpport"]', '25')
        self.assert_xml_equal('COMPONENTS/LABELFORM[@name="mailing-smtpsecurity"]', 'Aucune')
        self.assert_xml_equal('COMPONENTS/LABELFORM[@name="mailing-smtpuser"]', None)
        self.assert_xml_equal('COMPONENTS/LABELFORM[@name="mailing-smtppass"]', None)
        self.assert_xml_equal('COMPONENTS/LABELFORM[@name="mailing-msg-connection"]',
                              'Confirmation de connexion à votre application :\nAlias : %(username)s\nMot de passe : %(password)s\n')

    def test_tryemail_noconfig(self):
        configSMTP('', 25)
        self.assertEqual(0, self.server.count())
        self.factory.xfer = SendEmailTry()
        self.call('/lucterios.mailing/sendEmailTry', {}, False)
        self.assert_observer('core.exception', 'lucterios.mailing', 'sendEmailTry')
        self.assert_xml_equal("EXCEPTION/MESSAGE", "Mauvais paramètrage du courriel")
        self.assertEqual(0, self.server.count())

    def test_tryemail_success(self):
        configSMTP('localhost', 1025)
        self.assertEqual(0, self.server.count())
        self.factory.xfer = SendEmailTry()
        self.call('/lucterios.mailing/sendEmailTry', {}, False)
        self.assert_observer('core.dialogbox', 'lucterios.mailing', 'sendEmailTry')
        self.assert_xml_equal('TEXT', 'Courriel envoyé, veuillez le vérifier.')
        self.assertEqual(1, self.server.count())
        self.assertEqual('mr-sylvestre@worldcompany.com', self.server.get(0)[1])
        self.assertEqual(['mr-sylvestre@worldcompany.com'], self.server.get(0)[2])
        msg, = self.server.check_first_message('Essai de courriel', 1)
        self.assertEqual('text/plain', msg.get_content_type())
        self.assertEqual('base64', msg.get('Content-Transfer-Encoding', ''))
        self.assertEqual('Courriel envoyé pour vérifier la configuration\n\nWoldCompany\n', decode_b64(msg.get_payload())[:60])

    def test_send_no_config(self):
        configSMTP('', 25)
        self.assertEqual(0, self.server.count())
        self.assertEqual(False, will_mail_send())
        try:
            send_email('toto@machin.com', 'send without config', 'boom!!!')
            self.assertTrue(False)
        except LucteriosException as error:
            self.assertEqual(six.text_type(error), 'Courriel non configuré !')
        self.assertEqual(0, self.server.count())

    def test_send_bad_config(self):
        configSMTP('localhost', 1125)
        self.assertEqual(0, self.server.count())
        self.assertEqual(True, will_mail_send())
        try:
            send_email('toto@machin.com', 'send without config', 'boom!!!')
            self.assertTrue(False)
        except LucteriosException as error:
            self.assertEqual(six.text_type(error), '[Errno 111] Connection refused')
        self.assertEqual(0, self.server.count())

    def test_send_ok(self):
        configSMTP('localhost', 1025)
        self.assertEqual(0, self.server.count())
        self.assertEqual(True, will_mail_send())
        send_email('toto@machin.com', 'send correct config', 'Yessss!!!')
        self.assertEqual(1, self.server.count())
        self.assertEqual('mr-sylvestre@worldcompany.com', self.server.get(0)[1])
        self.assertEqual(['toto@machin.com'], self.server.get(0)[2])
        msg, = self.server.check_first_message('send correct config', 1)
        self.assertEqual('text/plain', msg.get_content_type())
        self.assertEqual('base64', msg.get('Content-Transfer-Encoding', ''))
        self.assertEqual('Yessss!!!', decode_b64(msg.get_payload()))
        self.assertEqual(None, self.server.smtp.auth_params)

    def test_send_copyhimself(self):
        configSMTP('localhost', 1025)
        self.assertEqual(0, self.server.count())
        self.assertEqual(True, will_mail_send())
        send_email('toto@machin.com', 'send correct config', 'Yessss!!!', withcopy=True)
        self.assertEqual(1, self.server.count())
        self.assertEqual('mr-sylvestre@worldcompany.com', self.server.get(0)[1])
        self.assertEqual(['toto@machin.com', 'mr-sylvestre@worldcompany.com'], self.server.get(0)[2])
        msg, = self.server.check_first_message('send correct config', 1)
        self.assertEqual('text/plain', msg.get_content_type())
        self.assertEqual('base64', msg.get('Content-Transfer-Encoding', ''))
        self.assertEqual('Yessss!!!', decode_b64(msg.get_payload()))
        self.assertEqual(None, self.server.smtp.auth_params)

    def test_send_multi_dest(self):
        configSMTP('localhost', 1025)
        self.assertEqual(0, self.server.count())
        self.assertEqual(True, will_mail_send())
        send_email(['toto@machin.com', 'titi@machin.com'], 'send correct config', 'Yessss!!!')
        self.assertEqual(1, self.server.count())
        self.assertEqual('mr-sylvestre@worldcompany.com', self.server.get(0)[1])
        self.assertEqual(['toto@machin.com', 'titi@machin.com'], self.server.get(0)[2])
        msg, = self.server.check_first_message('send correct config', 1, {'To': 'toto@machin.com, titi@machin.com', 'Cc': ''})
        self.assertEqual('text/plain', msg.get_content_type())
        self.assertEqual('base64', msg.get('Content-Transfer-Encoding', ''))
        self.assertEqual('Yessss!!!', decode_b64(msg.get_payload()))
        self.assertEqual(None, self.server.smtp.auth_params)

    def test_send_withcopy(self):
        configSMTP('localhost', 1025)
        self.assertEqual(0, self.server.count())
        self.assertEqual(True, will_mail_send())
        send_email('toto@machin.com', 'send correct config', 'Yessss!!!', cclist=['titi@machin.com', 'tutu@machin.com'])
        self.assertEqual(1, self.server.count())
        self.assertEqual('mr-sylvestre@worldcompany.com', self.server.get(0)[1])
        self.assertEqual(['toto@machin.com', 'titi@machin.com', 'tutu@machin.com'], self.server.get(0)[2])
        msg, = self.server.check_first_message('send correct config', 1, {'To': 'toto@machin.com', 'Cc': 'titi@machin.com, tutu@machin.com'})
        self.assertEqual('text/plain', msg.get_content_type())
        self.assertEqual('base64', msg.get('Content-Transfer-Encoding', ''))
        self.assertEqual('Yessss!!!', decode_b64(msg.get_payload()))
        self.assertEqual(None, self.server.smtp.auth_params)

    def test_send_withbindcopy(self):
        configSMTP('localhost', 1025)
        self.assertEqual(0, self.server.count())
        self.assertEqual(True, will_mail_send())
        send_email('toto@machin.com', 'send correct config', 'Yessss!!!', bcclist=['titi@machin.com', 'tutu@machin.com'])
        self.assertEqual(1, self.server.count())
        self.assertEqual('mr-sylvestre@worldcompany.com', self.server.get(0)[1])
        self.assertEqual(['toto@machin.com', 'titi@machin.com', 'tutu@machin.com'], self.server.get(0)[2])
        msg, = self.server.check_first_message('send correct config', 1, {'To': 'toto@machin.com', 'Cc': ''})
        self.assertEqual('text/plain', msg.get_content_type())
        self.assertEqual('base64', msg.get('Content-Transfer-Encoding', ''))
        self.assertEqual('Yessss!!!', decode_b64(msg.get_payload()))
        self.assertEqual(None, self.server.smtp.auth_params)

    def test_send_withdouble(self):
        configSMTP('localhost', 1025)
        self.assertEqual(0, self.server.count())
        self.assertEqual(True, will_mail_send())
        send_email(['toto@machin.com', 'titi@machin.com', 'tyty@machin.com'], 'send correct config', 'Yessss!!!',
                   cclist=['titi@machin.com', 'tutu@machin.com', 'tata@machin.com'], bcclist=['toto@machin.com', 'tutu@machin.com', 'tete@machin.com'])
        self.assertEqual(1, self.server.count())
        self.assertEqual('mr-sylvestre@worldcompany.com', self.server.get(0)[1])
        self.assertEqual(['toto@machin.com', 'titi@machin.com', 'tyty@machin.com', 'tutu@machin.com',
                          'tata@machin.com', 'tete@machin.com'], self.server.get(0)[2])
        msg, = self.server.check_first_message('send correct config', 1, {'To': 'toto@machin.com, titi@machin.com, tyty@machin.com',
                                                                          'Cc': 'tutu@machin.com, tata@machin.com'})
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
        self.assertEqual('mr-sylvestre@worldcompany.com', self.server.get(0)[1])
        self.assertEqual(['toto@machin.com'], self.server.get(0)[2])
        msg, = self.server.check_first_message('send html', 1)
        self.assertEqual('text/html', msg.get_content_type())
        self.assertEqual('base64', msg.get('Content-Transfer-Encoding', ''))
        self.assertEqual('<html><body><h1>Yessss!!!</h1></body></html>', decode_b64(msg.get_payload()))

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
            self.assertEqual(['', 'toto', 'abc123'], self.server.smtp.auth_params)

    def test_send_with_starttls(self):
        configSMTP('localhost', 1025, 1)
        self.assertEqual(0, self.server.count())
        self.assertEqual(True, will_mail_send())
        try:
            send_email('toto@machin.com', 'send with starttls', 'failed!')
            self.assertTrue(False)
        except LucteriosException as error:
            self.assertEqual(six.text_type(error), 'STARTTLS extension not supported by server.')
        self.assertEqual(0, self.server.count())

    def test_send_with_ssl(self):
        configSMTP('localhost', 1025, 2)
        self.assertEqual(0, self.server.count())
        self.assertEqual(True, will_mail_send())
        try:
            send_email('toto@machin.com', 'send with ssl', 'not success!')
            self.assertTrue(False)
        except LucteriosException as error:
            self.assertTrue('unknown protocol' in six.text_type(error), six.text_type(error))
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
            self.assertEqual('mr-sylvestre@worldcompany.com', self.server.get(0)[1])
            self.assertEqual(['toto@machin.com'], self.server.get(0)[2])
            msg, msg_f1, msg_f2 = self.server.check_first_message(
                'send with files', 3)
            self.assertEqual('text/plain', msg.get_content_type())
            self.assertEqual('base64', msg.get('Content-Transfer-Encoding', ''))
            self.assertEqual('2 files sent!', decode_b64(msg.get_payload()))
            self.assertEqual(None, self.server.smtp.auth_params)
            self.assertTrue('filename1.txt' in msg_f1.get('Content-Type', ''), msg_f1.get('Content-Type', ''))
            self.assertEqual('blablabla\blabla.', decode_b64(msg_f1.get_payload()))
            self.assertTrue('filename2.png' in msg_f2.get(
                'Content-Type', ''), msg_f2.get('Content-Type', ''))
            file2.seek(0, SEEK_END)
            self.assertEqual(file2.tell(), len(b64decode(msg_f2.get_payload())))
        finally:
            file1.close()
            file2.close()

    def test_user_withoutconfig(self):
        configSMTP('', 25)
        self.factory.xfer = UsersEdit()
        self.call('/CORE/usersEdit', {}, False)
        self.assert_observer('core.custom', 'CORE', 'usersEdit')
        self.assert_count_equal('COMPONENTS/*', 15)

    def test_user_withconfig(self):
        configSMTP('localhost', 1025)
        self.factory.xfer = UsersEdit()
        self.call('/CORE/usersEdit', {}, False)
        self.assert_observer('core.custom', 'CORE', 'usersEdit')
        self.assert_count_equal('COMPONENTS/*', 16)
        self.assert_attrib_equal('COMPONENTS/CHECK[@name="password_generate"]', "description", "Générer un nouveau mot de passe?")

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
        content_msg = decode_b64(msg.get_payload())
        self.assertEqual('Confirmation de connexion à votre application :\nAlias : admin\nMot de passe : ', decode_b64(msg.get_payload())[:77])
        password = content_msg[77:].strip()
        user = LucteriosUser.objects.get(id=1)
        self.assertTrue(user.check_password(password), content_msg)


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
        self.assert_observer('core.custom', 'lucterios.mailing', 'messageAddModify')
        self.assert_count_equal('COMPONENTS/*', 3)

        self.factory.xfer = MessageAddModify()
        self.call('/lucterios.mailing/messageAddModify', {'SAVE': 'YES', 'subject': 'new message', 'body':
                                                          '{[b]}{[font color="blue"]}All{[/font]}{[/b]}{[newline]}Small message to give a big {[u]}kiss{[/u]} ;){[newline]}{[newline]}Bye'}, False)
        self.assert_observer('core.acknowledge', 'lucterios.mailing', 'messageAddModify')

        self.factory.xfer = MessageList()
        self.call('/lucterios.mailing/messageList', {}, False)
        self.assert_observer('core.custom', 'lucterios.mailing', 'messageList')
        self.assert_count_equal('COMPONENTS/GRID[@name="message"]/RECORD', 1)
        self.assert_xml_equal('COMPONENTS/GRID[@name="message"]/RECORD[1]/VALUE[@name="status"]', "ouvert")
        self.assert_xml_equal('COMPONENTS/GRID[@name="message"]/RECORD[1]/VALUE[@name="date"]', '---')
        self.assert_xml_equal('COMPONENTS/GRID[@name="message"]/RECORD[1]/VALUE[@name="subject"]', 'new message')

        self.factory.xfer = MessageDel()
        self.call('/lucterios.mailing/messageDel',
                  {'message': '1', 'CONFIRME': 'YES'}, False)
        self.assert_observer('core.acknowledge', 'lucterios.mailing', 'messageDel')

        self.factory.xfer = MessageList()
        self.call('/lucterios.mailing/messageList', {}, False)
        self.assert_observer('core.custom', 'lucterios.mailing', 'messageList')
        self.assert_count_equal('COMPONENTS/GRID[@name="message"]/RECORD', 0)

    def test_show_message(self):
        self.factory.xfer = MessageAddModify()
        self.call('/lucterios.mailing/messageAddModify', {'SAVE': 'YES', 'subject': 'new message', 'body':
                                                          '{[b]}{[font color="blue"]}All{[/font]}{[/b]}{[newline]}Small message to give a big {[u]}kiss{[/u]} ;){[newline]}{[newline]}Bye'}, False)
        self.assert_observer('core.acknowledge', 'lucterios.mailing', 'messageAddModify')

        self.factory.xfer = MessageShow()
        self.call('/lucterios.mailing/messageShow', {'message': '1'}, False)
        self.assert_observer('core.custom', 'lucterios.mailing', 'messageShow')
        self.assert_count_equal('COMPONENTS/*', 7)
        self.assert_count_equal('ACTIONS/ACTION', 2)
        self.assert_action_equal('ACTIONS/ACTION[1]', ('Modifier', 'images/edit.png', 'lucterios.mailing', 'messageAddModify', 1, 1, 1))
        self.assert_action_equal('ACTIONS/ACTION[2]', ('Fermer', 'images/close.png'))
        self.assert_count_equal('COMPONENTS/GRID[@name="recipient_list"]/RECORD', 0)

        self.factory.xfer = MessageValidRecipient()
        self.call('/lucterios.mailing/messageValidRecipient',
                  {'message': '1', 'modelname': 'contacts.Individual', 'CRITERIA': 'genre||8||1'}, False)
        self.assert_observer('core.acknowledge', 'lucterios.mailing', 'messageValidRecipient')
        self.factory.xfer = MessageValidRecipient()
        self.call('/lucterios.mailing/messageValidRecipient',
                  {'message': '1', 'modelname': 'contacts.AbstractContact', 'CRITERIA': ''}, False)
        self.assert_observer('core.acknowledge', 'lucterios.mailing', 'messageValidRecipient')
        self.factory.xfer = MessageValidRecipient()
        self.call('/lucterios.mailing/messageValidRecipient',
                  {'message': '1', 'modelname': 'contacts.LegalEntity', 'CRITERIA': 'name||5||truc'}, False)
        self.assert_observer('core.acknowledge', 'lucterios.mailing', 'messageValidRecipient')

        self.factory.xfer = MessageShow()
        self.call('/lucterios.mailing/messageShow', {'message': '1'}, False)
        self.assert_observer('core.custom', 'lucterios.mailing', 'messageShow')
        self.assert_count_equal('COMPONENTS/*', 8)
        self.assert_count_equal('ACTIONS/ACTION', 3)
        self.assert_action_equal('ACTIONS/ACTION[1]', ('Valider', 'images/transition.png', 'lucterios.mailing', 'messageTransition', 0, 1, 1, {'TRANSITION': 'valid'}))
        self.assert_action_equal('ACTIONS/ACTION[2]', ('Modifier', 'images/edit.png', 'lucterios.mailing', 'messageAddModify', 1, 1, 1))
        self.assert_action_equal('ACTIONS/ACTION[3]', ('Fermer', 'images/close.png'))
        self.assert_xml_equal('COMPONENTS/LABELFORM[@name="status"]', 'ouvert')
        self.assert_count_equal('COMPONENTS/GRID[@name="recipient_list"]/ACTIONS/ACTION', 2)
        self.assert_count_equal('COMPONENTS/GRID[@name="recipient_list"]/RECORD', 3)
        self.assert_xml_equal('COMPONENTS/GRID[@name="recipient_list"]/RECORD[1]/VALUE[@name="model"]', "Personne Physique")
        self.assert_xml_equal('COMPONENTS/GRID[@name="recipient_list"]/RECORD[1]/VALUE[@name="filter"]', '{[b]}genre{[/b]} égal {[i]}"Homme"{[/i]}')
        self.assert_xml_equal('COMPONENTS/GRID[@name="recipient_list"]/RECORD[2]/VALUE[@name="model"]', "Contact Générique")
        self.assert_xml_equal('COMPONENTS/GRID[@name="recipient_list"]/RECORD[3]/VALUE[@name="model"]', "Personne Morale")

        self.factory.xfer = MessageDelRecipient()
        self.call('/lucterios.mailing/messageDelRecipient',
                  {'message': '1', 'recipient_list': '1', 'CONFIRME': 'YES'}, False)
        self.assert_observer('core.acknowledge', 'lucterios.mailing', 'messageDelRecipient')

        self.factory.xfer = MessageShow()
        self.call('/lucterios.mailing/messageShow', {'message': '1'}, False)
        self.assert_observer('core.custom', 'lucterios.mailing', 'messageShow')
        self.assert_count_equal('COMPONENTS/*', 8)
        self.assert_count_equal('COMPONENTS/GRID[@name="recipient_list"]/RECORD', 2)

    def test_validate_message(self):
        configSMTP('', 25)
        self.assertFalse(will_mail_send(), 'no email')
        self.factory.xfer = MessageAddModify()
        self.call('/lucterios.mailing/messageAddModify', {'SAVE': 'YES', 'subject': 'new message', 'body':
                                                          '{[b]}{[font color="blue"]}All{[/font]}{[/b]}{[newline]}Small message to give a big {[u]}kiss{[/u]} ;){[newline]}{[newline]}Bye'}, False)
        self.factory.xfer = MessageValidRecipient()
        self.call('/lucterios.mailing/messageValidRecipient',
                  {'message': '1', 'modelname': 'contacts.Individual', 'CRITERIA': 'genre||8||1'}, False)
        self.factory.xfer = MessageValidRecipient()
        self.call('/lucterios.mailing/messageValidRecipient',
                  {'message': '1', 'modelname': 'contacts.LegalEntity', 'CRITERIA': ''}, False)
        self.factory.xfer = MessageTransition()
        self.call('/lucterios.mailing/messageTransition',
                  {'message': '1', 'TRANSITION': 'valid', 'CONFIRME': 'YES'}, False)
        self.assert_observer('core.acknowledge', 'lucterios.mailing', 'messageTransition')

        self.assertFalse(will_mail_send(), 'no email')
        self.factory.xfer = MessageShow()
        self.call('/lucterios.mailing/messageShow', {'message': '1'}, False)
        self.assert_observer('core.custom', 'lucterios.mailing', 'messageShow')
        self.assert_count_equal('COMPONENTS/*', 8)
        self.assert_xml_equal('COMPONENTS/LABELFORM[@name="status"]', 'fermé')
        self.assert_count_equal('COMPONENTS/GRID[@name="recipient_list"]/ACTIONS/ACTION', 0)
        self.assert_count_equal('COMPONENTS/GRID[@name="recipient_list"]/RECORD', 2)
        self.assert_xml_equal('COMPONENTS/LABELFORM[@name="contact_nb"]', 'Message défini pour 2 contacts')
        self.assert_count_equal('ACTIONS/ACTION', 2)
        self.assert_action_equal(
            'ACTIONS/ACTION[1]', ('Lettres', 'lucterios.mailing/images/letter.png', 'lucterios.mailing', 'messageLetter', 0, 1, 1))
        self.assert_action_equal('ACTIONS/ACTION[2]', ('Fermer', 'images/close.png'))

        configSMTP('localhost', 1025)
        self.assertTrue(will_mail_send(), 'with email')
        self.factory.xfer = MessageShow()
        self.call('/lucterios.mailing/messageShow', {'message': '1'}, False)
        self.assert_observer('core.custom', 'lucterios.mailing', 'messageShow')
        self.assert_count_equal('ACTIONS/ACTION', 3)
        self.assert_action_equal(
            'ACTIONS/ACTION[1]', ('Lettres', 'lucterios.mailing/images/letter.png', 'lucterios.mailing', 'messageLetter', 0, 1, 1))
        self.assert_action_equal(
            'ACTIONS/ACTION[2]', ('Courriels', 'lucterios.mailing/images/email.png', 'lucterios.mailing', 'messageEmail', 0, 1, 1))
        self.assert_action_equal('ACTIONS/ACTION[3]', ('Fermer', 'images/close.png'))

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
        self.factory.xfer = MessageTransition()
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
            self.assertEqual('mr-sylvestre@worldcompany.com', server.get(0)[1])
            self.assertEqual(['mr-sylvestre@worldcompany.com'], server.get(0)[2])
            msg, = server.check_first_message('new message', 1)
            self.assertEqual('text/html', msg.get_content_type())
            self.assertEqual('base64', msg.get('Content-Transfer-Encoding', ''))
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
        self.factory.xfer = MessageTransition()
        self.call('/lucterios.mailing/messageValid', {'message': '1', 'CONFIRME': 'YES'}, False)

        self.factory.xfer = MessageLetter()
        self.call('/lucterios.mailing/messageLetter', {'message': '1'}, False)
        self.assert_observer('core.custom', 'lucterios.mailing', 'messageLetter')
        self.assert_xml_equal('COMPONENTS/SELECT[@name="MODEL"]', '5')

        self.factory.xfer = MessageLetter()
        self.call('/lucterios.mailing/messageLetter',
                  {'message': '1', 'PRINT_MODE': '3', 'MODEL': 5}, False)
        self.assert_observer('core.print', 'lucterios.mailing', 'messageLetter')
        pdf_value = b64decode(six.text_type(self.get_first_xpath('PRINT').text))
        self.assertEqual(pdf_value[:4], "%PDF".encode('ascii', 'ignore'))


class UserTest(LucteriosTest):

    def setUp(self):
        self.xfer_class = XferContainerAcknowledge
        LucteriosTest.setUp(self)
        self.factory.user = AnonymousUser()
        change_ourdetail()
        create_jack(LucteriosUser.objects.create(first_name='jack', last_name='MISTER', username='jack', email='jack@worldcompany.com'))

    def test_pwd_forget(self):
        configSMTP('localhost', 1025)
        self.factory.xfer = AskPassword()
        self.call('/lucterios.CORE/askPassword', {}, False)
        self.assert_observer('core.custom', 'lucterios.CORE', 'askPassword')
        self.assert_count_equal('CONTEXT', 0)
        self.assert_count_equal('COMPONENTS/*', 3)
        self.assert_xml_equal('COMPONENTS/EDIT[@name="email"]', None)
        self.assert_count_equal('ACTIONS/ACTION', 2)

        server = TestReceiver()
        server.start(1025)
        try:
            self.assertEqual(0, server.count())

            self.factory.xfer = AskPasswordAct()
            self.call('/lucterios.CORE/askPasswordAct', {"email": "inconnu@worldcompany.com"}, False)
            self.assert_observer('core.acknowledge', 'lucterios.CORE', 'askPasswordAct')
            self.assertEqual(0, server.count())

            self.factory.xfer = AskPasswordAct()
            self.call('/lucterios.CORE/askPasswordAct', {"email": "jack@worldcompany.com"}, False)
            self.assert_observer('core.acknowledge', 'lucterios.CORE', 'askPasswordAct')
            self.assertEqual(1, server.count())
            self.assertEqual('mr-sylvestre@worldcompany.com', server.get(0)[1])
            self.assertEqual(['jack@worldcompany.com'], server.get(0)[2])
            msg, = server.check_first_message('Mot de passe de connexion', 1)
            self.assertEqual('text/plain', msg.get_content_type())
            self.assertEqual('base64', msg.get('Content-Transfer-Encoding', ''))
            message = decode_b64(msg.get_payload())
            self.assertEqual('Confirmation de connexion à votre application :\nAlias : jack\nMot de passe : ', message[:76])
            password = message[76:]
        finally:
            server.stop()
        user = LucteriosUser.objects.get(id=2)
        self.assertTrue(user.check_password(password), 'success after change')

    def test_no_new_account(self):
        self.factory.xfer = CreateAccount()
        self.call('/lucterios.contact/createAccount', {}, False)
        self.assert_observer('core.exception', 'lucterios.contact', 'createAccount')

    def test_new_account(self):
        param = Parameter.objects.get(name='contacts-createaccount')
        param.value = '1'
        param.save()
        configSMTP('localhost', 1025)

        self.factory.xfer = CreateAccount()
        self.call('/lucterios.contact/createAccount', {}, False)
        self.assert_observer('core.custom', 'lucterios.contact', 'createAccount')
        self.assert_count_equal('CONTEXT', 0)
        self.assert_count_equal('COMPONENTS/*', 8)
        self.assert_xml_equal('COMPONENTS/SELECT[@name="genre"]', '1')
        self.assert_xml_equal('COMPONENTS/EDIT[@name="firstname"]', None)
        self.assert_xml_equal('COMPONENTS/EDIT[@name="lastname"]', None)
        self.assert_xml_equal('COMPONENTS/EDIT[@name="username"]', None)
        self.assert_xml_equal('COMPONENTS/EDIT[@name="email"]', None)
        self.assert_xml_equal('COMPONENTS/CAPTCHA[@name="captcha"]', None)
        self.assert_count_equal('ACTIONS/ACTION', 2)

        server = TestReceiver()
        server.start(1025)
        try:
            self.factory.xfer = CreateAccount()
            self.call('/lucterios.contacts/createAccount', {'SAVE': 'YES', 'firstname': 'pierre', 'genre': 1,
                                                            'lastname': 'DUPONT', 'username': 'admin', 'email': 'pierre@worldcompany.com'}, False)
            self.assert_observer('core.acknowledge', 'lucterios.contacts', 'createAccount')
            self.assert_count_equal('CONTEXT/PARAM', 6)
            self.assert_count_equal('ACTION', 1)
            self.assert_action_equal('ACTION', (None, None, 'lucterios.contacts', 'createAccount', 1, 1, 1, {
                                     "SAVE": None, "error": "Ce compte existe déjà !"}))
            self.assertEqual(0, server.count())

            self.factory.xfer = CreateAccount()
            self.call('/lucterios.contacts/createAccount', {'SAVE': 'YES', 'firstname': 'pierre', 'genre': 1,
                                                            'lastname': 'DUPONT', 'username': 'pierre', 'email': 'pierre@worldcompany.com'}, False)
            self.assert_observer('core.dialogbox', 'lucterios.contacts', 'createAccount')
            self.assert_xml_equal('TEXT', 'Votre compte est créé{[br/]}Vous allez recevoir un courriel avec votre mot de passe.')
            self.assertEqual(1, server.count())
            self.assertEqual('mr-sylvestre@worldcompany.com', server.get(0)[1])
            self.assertEqual(['pierre@worldcompany.com'], server.get(0)[2])
            msg, = server.check_first_message('Mot de passe de connexion', 1)
            self.assertEqual('text/plain', msg.get_content_type())
            self.assertEqual('base64', msg.get('Content-Transfer-Encoding', ''))
            message = decode_b64(msg.get_payload())
            self.assertEqual('Confirmation de connexion à votre application :\nAlias : pierre\nMot de passe : ', message[:78])
            password = message[78:]
        finally:
            server.stop()
        user = LucteriosUser.objects.get(id=3)
        self.assertEqual('pierre', user.first_name)
        self.assertEqual('DUPONT', user.last_name)
        self.assertEqual('pierre', user.username)
        self.assertEqual('pierre@worldcompany.com', user.email)
        self.assertTrue(user.check_password(password), 'success after change')
        cont = Individual.objects.filter(user=user)
        self.assertEqual(1, len(cont))
        self.assertEqual('pierre', cont[0].firstname)
        self.assertEqual('DUPONT', cont[0].lastname)
        self.assertEqual(1, cont[0].genre)
        self.assertEqual('pierre@worldcompany.com', cont[0].email)
        self.assertEqual('---', cont[0].address)
        self.assertEqual('---', cont[0].postal_code)
        self.assertEqual('---', cont[0].city)
        moral = LegalEntity.objects.filter(responsability__individual__user=user)
        self.assertEqual(0, len(moral))
        self.assertEqual(1, len(LegalEntity.objects.all()))

    def test_new_account_with_structure(self):
        param = Parameter.objects.get(name='contacts-createaccount')
        param.value = '2'
        param.save()
        configSMTP('localhost', 1025)

        self.factory.xfer = CreateAccount()
        self.call('/lucterios.contact/createAccount', {}, False)
        self.assert_observer('core.custom', 'lucterios.contact', 'createAccount')
        self.assert_count_equal('CONTEXT', 0)
        self.assert_count_equal('COMPONENTS/*', 9)
        self.assert_xml_equal('COMPONENTS/SELECT[@name="genre"]', '1')
        self.assert_xml_equal('COMPONENTS/EDIT[@name="firstname"]', None)
        self.assert_xml_equal('COMPONENTS/EDIT[@name="lastname"]', None)
        self.assert_xml_equal('COMPONENTS/EDIT[@name="username"]', None)
        self.assert_xml_equal('COMPONENTS/EDIT[@name="email"]', None)
        self.assert_xml_equal('COMPONENTS/EDIT[@name="legalentity"]', None)
        self.assert_xml_equal('COMPONENTS/CAPTCHA[@name="captcha"]', None)
        self.assert_count_equal('ACTIONS/ACTION', 2)

        server = TestReceiver()
        server.start(1025)
        try:
            self.factory.xfer = CreateAccount()
            self.call('/lucterios.contacts/createAccount', {'SAVE': 'YES', 'firstname': 'pierre', 'genre': 1, 'legalentity': 'Chez moi',
                                                            'lastname': 'DUPONT', 'username': 'pierre', 'email': 'pierre@worldcompany.com'}, False)
            self.assert_observer('core.dialogbox', 'lucterios.contacts', 'createAccount')
            self.assert_xml_equal('TEXT', 'Votre compte est créé{[br/]}Vous allez recevoir un courriel avec votre mot de passe.')
            self.assertEqual(1, server.count())
            self.assertEqual('mr-sylvestre@worldcompany.com', server.get(0)[1])
            self.assertEqual(['pierre@worldcompany.com'], server.get(0)[2])
            msg, = server.check_first_message('Mot de passe de connexion', 1)
            self.assertEqual('text/plain', msg.get_content_type())
            self.assertEqual('base64', msg.get('Content-Transfer-Encoding', ''))
            message = decode_b64(msg.get_payload())
            self.assertEqual('Confirmation de connexion à votre application :\nAlias : pierre\nMot de passe : ', message[:78])
            password = message[78:]
        finally:
            server.stop()
        user = LucteriosUser.objects.get(id=3)
        self.assertEqual('pierre', user.username)
        self.assertTrue(user.check_password(password), 'success after change')
        cont = Individual.objects.filter(user=user)
        self.assertEqual(1, len(cont))
        self.assertEqual('pierre', cont[0].firstname)
        moral = LegalEntity.objects.filter(responsability__individual__user=user)
        self.assertEqual(1, len(moral))
        self.assertEqual('Chez moi', moral[0].name)
        self.assertEqual('pierre@worldcompany.com', moral[0].email)
        self.assertEqual('---', moral[0].address)
        self.assertEqual('---', moral[0].postal_code)
        self.assertEqual('---', moral[0].city)
        self.assertEqual(2, len(LegalEntity.objects.all()))
