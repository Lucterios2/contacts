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
from time import sleep

from django.utils import six

from lucterios.framework.test import LucteriosTest, AsychronousLucteriosTest
from lucterios.framework.filetools import get_user_dir
from lucterios.framework.error import LucteriosException
from lucterios.framework.tools import get_binay
from lucterios.framework.models import LucteriosScheduler
from lucterios.CORE.models import Parameter, LucteriosUser
from lucterios.CORE.views_usergroup import UsersEdit
from lucterios.CORE.views import AskPassword, AskPasswordAct

from lucterios.contacts.tests_contacts import change_ourdetail, create_jack
from lucterios.contacts.views import CreateAccount
from lucterios.contacts.models import Individual, LegalEntity

from lucterios.mailing.views import Configuration, SendEmailTry
from lucterios.mailing.functions import will_mail_send, send_email
from lucterios.mailing.views_message import MessageAddModify, MessageList, MessageDel, MessageShow, MessageValidRecipient,\
    MessageDelRecipient, MessageLetter, MessageTransition, MessageInsertDoc,\
    MessageValidInsertDoc, MessageRemoveDoc
from django.contrib.auth.models import AnonymousUser
from lucterios.mailing.test_tools import configSMTP, decode_b64, TestReceiver
from lucterios.documents.tests import create_doc


class ConfigurationTest(LucteriosTest):

    def __init__(self, methodName):
        LucteriosTest.__init__(self, methodName)
        self.server = TestReceiver()

    def setUp(self):
        change_ourdetail()
        LucteriosTest.setUp(self)
        rmtree(get_user_dir(), True)
        self.server.start(1025)

    def tearDown(self):
        self.server.stop()
        LucteriosTest.tearDown(self)

    def test_config(self):
        self.factory.xfer = Configuration()
        self.calljson('/lucterios.mailing/configuration', {}, False)
        self.assert_observer('core.custom', 'lucterios.mailing', 'configuration')
        self.assertEqual(len(self.json_context), 0)
        self.assert_count_equal('', 2 + 8 + 2 + 2)
        self.assert_json_equal('LABELFORM', "mailing-smtpserver", '')
        self.assert_json_equal('LABELFORM', "mailing-smtpport", '25')
        self.assert_json_equal('LABELFORM', "mailing-smtpsecurity", 'Aucune')
        self.assert_json_equal('LABELFORM', "mailing-smtpuser", '')
        self.assert_json_equal('LABELFORM', "mailing-smtppass", '')
        self.assert_json_equal('LABELFORM', "mailing-msg-connection",
                               'Bienvenue{[br/]}{[br/]}Confirmation de connexion à votre application :{[br/]} - Alias : %(username)s{[br/]} - Mot de passe : %(password)s{[br/]}{[br/]}Salutations{[br/]}')
        self.assert_json_equal('LABELFORM', "mailing-delay-batch", '15.0')
        self.assert_json_equal('LABELFORM', "mailing-nb-by-batch", '10')

    def test_tryemail_noconfig(self):
        configSMTP('', 25)
        self.assertEqual(0, self.server.count())
        self.factory.xfer = SendEmailTry()
        self.calljson('/lucterios.mailing/sendEmailTry', {}, False)
        self.assert_observer('core.exception', 'lucterios.mailing', 'sendEmailTry')
        self.assert_json_equal('', "message", "Mauvais paramètrage du courriel")
        self.assertEqual(0, self.server.count())

    def test_tryemail_success(self):
        configSMTP('localhost', 1025)
        self.assertEqual(0, self.server.count())
        self.factory.xfer = SendEmailTry()
        self.calljson('/lucterios.mailing/sendEmailTry', {}, False)
        self.assert_observer('core.dialogbox', 'lucterios.mailing', 'sendEmailTry')
        self.assert_json_equal('', 'text', 'Courriel envoyé, veuillez le vérifier.')
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

    def test_send_multi_email(self):
        configSMTP('localhost', 1025)
        self.assertEqual(0, self.server.count())
        self.assertEqual(True, will_mail_send())
        send_email(['toto@machin.com;titi@machin.com,tutu@machin.com'], 'send correct config', 'Yessss!!!')
        self.assertEqual(1, self.server.count())
        self.assertEqual('mr-sylvestre@worldcompany.com', self.server.get(0)[1])
        self.assertEqual(['toto@machin.com', 'titi@machin.com', 'tutu@machin.com'], self.server.get(0)[2])
        msg, = self.server.check_first_message('send correct config', 1, {'To': 'toto@machin.com, titi@machin.com, tutu@machin.com', 'Cc': ''})
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
            send_email('toto@machin.com', 'send with files', '2 files sent!', [('filename1.txt', file1), ('filename2.png', file2)])
            self.assertEqual(1, self.server.count())
            self.assertEqual('mr-sylvestre@worldcompany.com', self.server.get(0)[1])
            self.assertEqual(['toto@machin.com'], self.server.get(0)[2])
            msg, msg_f1, msg_f2 = self.server.check_first_message('send with files', 3)
            self.assertEqual('text/plain', msg.get_content_type())
            self.assertEqual('base64', msg.get('Content-Transfer-Encoding', ''))
            self.assertEqual('2 files sent!', decode_b64(msg.get_payload()))
            self.assertEqual(None, self.server.smtp.auth_params)
            self.assertTrue('filename1.txt' in msg_f1.get('Content-Type', ''), msg_f1.get('Content-Type', ''))
            self.assertEqual('blablabla\blabla.', decode_b64(msg_f1.get_payload()))
            self.assertTrue('filename2.png' in msg_f2.get('Content-Type', ''), msg_f2.get('Content-Type', ''))
            file2.seek(0, SEEK_END)
            self.assertEqual(file2.tell(), len(b64decode(msg_f2.get_payload())))
        finally:
            file1.close()
            file2.close()

    def test_user_withoutconfig(self):
        configSMTP('', 25)
        self.factory.xfer = UsersEdit()
        self.calljson('/CORE/usersEdit', {}, False)
        self.assert_observer('core.custom', 'CORE', 'usersEdit')
        self.assert_count_equal('', 15)

    def test_user_withconfig(self):
        configSMTP('localhost', 1025)
        self.factory.xfer = UsersEdit()
        self.calljson('/CORE/usersEdit', {}, False)
        self.assert_observer('core.custom', 'CORE', 'usersEdit')
        self.assert_count_equal('', 16)
        self.assert_attrib_equal("password_generate", "description", "Générer un nouveau mot de passe?")

    def test_user_change_password(self):
        configSMTP('localhost', 1025)
        self.assertEqual(0, self.server.count())
        self.factory.xfer = UsersEdit()
        self.calljson('/CORE/usersEdit', {'SAVE': 'YES', 'user_actif': '1',
                                          "password_generate": 'o', "email": 'admin@super.com'}, False)
        self.assert_observer('core.acknowledge', 'CORE', 'usersEdit')
        self.assertEqual(1, self.server.count())
        msg, = self.server.check_first_message('Mot de passe de connexion', 1)
        self.assertEqual('text/html', msg.get_content_type())
        self.assertEqual('base64', msg.get('Content-Transfer-Encoding', ''))
        content_msg = decode_b64(msg.get_payload())
        self.assertEqual('<html>Bienvenue<br/><br/>Confirmation de connexion à votre application :'
                         '<br/> - Alias : admin<br/> - Mot de passe : ', content_msg[:116])
        password = content_msg[116:].split('<br/>')[0]
        user = LucteriosUser.objects.get(id=1)
        self.assertTrue(user.check_password(password), content_msg)


class MailingTest(LucteriosTest):

    def setUp(self):
        LucteriosTest.setUp(self)
        change_ourdetail()
        create_jack(firstname="jack", lastname="MISTER", with_email=True)
        create_jack(firstname="jean", lastname="Valjean", with_email=False)

    def test_messages(self):
        self.factory.xfer = MessageList()
        self.calljson('/lucterios.mailing/messageList', {}, False)
        self.assert_observer('core.custom', 'lucterios.mailing', 'messageList')
        self.assert_count_equal("message", 0)

        self.factory.xfer = MessageAddModify()
        self.calljson('/lucterios.mailing/messageAddModify', {}, False)
        self.assert_observer('core.custom', 'lucterios.mailing', 'messageAddModify')
        self.assert_count_equal('', 3)

        self.factory.xfer = MessageAddModify()
        self.calljson('/lucterios.mailing/messageAddModify', {'SAVE': 'YES', 'subject': 'new message', 'body':
                                                              '{[b]}{[font color="blue"]}All{[/font]}{[/b]}{[newline]}Small message to give a big {[u]}kiss{[/u]} ;){[newline]}{[newline]}Bye'}, False)
        self.assert_observer('core.acknowledge', 'lucterios.mailing', 'messageAddModify')

        self.factory.xfer = MessageList()
        self.calljson('/lucterios.mailing/messageList', {}, False)
        self.assert_observer('core.custom', 'lucterios.mailing', 'messageList')
        self.assert_count_equal("message", 1)
        self.assert_json_equal('', "message/@0/status", "ouvert")
        self.assert_json_equal('', "message/@0/date", '---')
        self.assert_json_equal('', "message/@0/subject", 'new message')

        self.factory.xfer = MessageDel()
        self.calljson('/lucterios.mailing/messageDel',
                      {'message': '1', 'CONFIRME': 'YES'}, False)
        self.assert_observer('core.acknowledge', 'lucterios.mailing', 'messageDel')

        self.factory.xfer = MessageList()
        self.calljson('/lucterios.mailing/messageList', {}, False)
        self.assert_observer('core.custom', 'lucterios.mailing', 'messageList')
        self.assert_count_equal("message", 0)

    def test_show_message(self):
        self.factory.xfer = MessageAddModify()
        self.calljson('/lucterios.mailing/messageAddModify', {'SAVE': 'YES', 'subject': 'new message', 'body':
                                                              '{[b]}{[font color="blue"]}All{[/font]}{[/b]}{[newline]}Small message to give a big {[u]}kiss{[/u]} ;){[newline]}{[newline]}Bye'}, False)
        self.assert_observer('core.acknowledge', 'lucterios.mailing', 'messageAddModify')

        self.factory.xfer = MessageShow()
        self.calljson('/lucterios.mailing/messageShow', {'message': '1'}, False)
        self.assert_observer('core.custom', 'lucterios.mailing', 'messageShow')
        self.assert_count_equal('', 10)
        self.assertEqual(len(self.json_actions), 2)
        self.assert_action_equal(self.json_actions[0], ('Modifier', 'images/edit.png', 'lucterios.mailing', 'messageAddModify', 1, 1, 1))
        self.assert_action_equal(self.json_actions[1], ('Fermer', 'images/close.png'))
        self.assert_count_equal("recipient_list", 0)

        self.factory.xfer = MessageValidRecipient()
        self.calljson('/lucterios.mailing/messageValidRecipient',
                      {'message': '1', 'modelname': 'contacts.Individual', 'CRITERIA': 'genre||8||1'}, False)
        self.assert_observer('core.acknowledge', 'lucterios.mailing', 'messageValidRecipient')
        self.factory.xfer = MessageValidRecipient()
        self.calljson('/lucterios.mailing/messageValidRecipient',
                      {'message': '1', 'modelname': 'contacts.AbstractContact', 'CRITERIA': ''}, False)
        self.assert_observer('core.acknowledge', 'lucterios.mailing', 'messageValidRecipient')
        self.factory.xfer = MessageValidRecipient()
        self.calljson('/lucterios.mailing/messageValidRecipient',
                      {'message': '1', 'modelname': 'contacts.LegalEntity', 'CRITERIA': 'name||5||truc'}, False)
        self.assert_observer('core.acknowledge', 'lucterios.mailing', 'messageValidRecipient')

        self.factory.xfer = MessageShow()
        self.calljson('/lucterios.mailing/messageShow', {'message': '1'}, False)
        self.assert_observer('core.custom', 'lucterios.mailing', 'messageShow')
        self.assert_count_equal('', 11)
        self.assertEqual(len(self.json_actions), 3)
        self.assert_action_equal(self.json_actions[0], ('Valider', 'images/transition.png', 'lucterios.mailing', 'messageTransition', 0, 1, 1, {'TRANSITION': 'valid'}))
        self.assert_action_equal(self.json_actions[1], ('Modifier', 'images/edit.png', 'lucterios.mailing', 'messageAddModify', 1, 1, 1))
        self.assert_action_equal(self.json_actions[2], ('Fermer', 'images/close.png'))
        self.assert_json_equal('LABELFORM', "status", 'ouvert')
        self.assert_count_equal("#recipient_list/actions", 2)
        self.assert_count_equal("recipient_list", 3)
        self.assert_json_equal('', "recipient_list/@0/model", "Personne Physique")
        self.assert_json_equal('', "recipient_list/@0/filter", '{[b]}genre{[/b]} égal {[i]}"Homme"{[/i]}')
        self.assert_json_equal('', "recipient_list/@1/model", "Contact Générique")
        self.assert_json_equal('', "recipient_list/@2/model", "Personne Morale")

        self.factory.xfer = MessageDelRecipient()
        self.calljson('/lucterios.mailing/messageDelRecipient',
                      {'message': '1', 'recipient_list': '1', 'CONFIRME': 'YES'}, False)
        self.assert_observer('core.acknowledge', 'lucterios.mailing', 'messageDelRecipient')

        self.factory.xfer = MessageShow()
        self.calljson('/lucterios.mailing/messageShow', {'message': '1'}, False)
        self.assert_observer('core.custom', 'lucterios.mailing', 'messageShow')
        self.assert_count_equal('', 11)
        self.assert_count_equal("recipient_list", 2)

    def test_validate_message(self):
        configSMTP('', 25)
        self.assertFalse(will_mail_send(), 'no email')
        self.factory.xfer = MessageAddModify()
        self.calljson('/lucterios.mailing/messageAddModify', {'SAVE': 'YES', 'subject': 'new message', 'body':
                                                              '{[b]}{[font color="blue"]}All{[/font]}{[/b]}{[newline]}Small message to give a big {[u]}kiss{[/u]} ;){[newline]}{[newline]}Bye'}, False)
        self.factory.xfer = MessageValidRecipient()
        self.calljson('/lucterios.mailing/messageValidRecipient', {'message': '1', 'modelname': 'contacts.Individual', 'CRITERIA': 'genre||8||1'}, False)
        self.factory.xfer = MessageValidRecipient()
        self.calljson('/lucterios.mailing/messageValidRecipient', {'message': '1', 'modelname': 'contacts.LegalEntity', 'CRITERIA': ''}, False)
        self.factory.xfer = MessageTransition()
        self.calljson('/lucterios.mailing/messageTransition', {'message': '1', 'TRANSITION': 'valid', 'CONFIRME': 'YES'}, False)
        self.assert_observer('core.acknowledge', 'lucterios.mailing', 'messageTransition')

        self.assertFalse(will_mail_send(), 'no email')
        self.factory.xfer = MessageShow()
        self.calljson('/lucterios.mailing/messageShow', {'message': '1'}, False)
        self.assert_observer('core.custom', 'lucterios.mailing', 'messageShow')
        self.assert_count_equal('', 11)
        self.assert_json_equal('LABELFORM', "status", 'validé')
        self.assert_count_equal("#recipient_list/actions", 0)
        self.assert_count_equal("recipient_list", 2)
        self.assert_json_equal('LABELFORM', "contact_nb", '3')
        self.assertEqual(len(self.json_actions), 2)
        self.assert_action_equal(self.json_actions[0], ('Lettres', 'lucterios.mailing/images/letter.png', 'lucterios.mailing', 'messageLetter', 0, 1, 1))
        self.assert_action_equal(self.json_actions[1], ('Fermer', 'images/close.png'))

        configSMTP('localhost', 1025)
        self.assertTrue(will_mail_send(), 'with email')
        self.factory.xfer = MessageShow()
        self.calljson('/lucterios.mailing/messageShow', {'message': '1'}, False)
        self.assert_observer('core.custom', 'lucterios.mailing', 'messageShow')
        self.assert_count_equal('', 12)
        self.assert_json_equal('LABELFORM', "contact_noemail", 'Valjean jean')
        self.assertEqual(len(self.json_actions), 3)
        self.assert_action_equal(self.json_actions[0], ('Courriels', 'lucterios.mailing/images/mailing.png', 'lucterios.mailing', 'messageTransition', 0, 1, 1, {'TRANSITION': 'sending'}))
        self.assert_action_equal(self.json_actions[1], ('Lettres', 'lucterios.mailing/images/letter.png', 'lucterios.mailing', 'messageLetter', 0, 1, 1))
        self.assert_action_equal(self.json_actions[2], ('Fermer', 'images/close.png'))

    def test_letter_message(self):
        self.factory.xfer = MessageAddModify()
        self.calljson('/lucterios.mailing/messageAddModify', {'SAVE': 'YES', 'subject': 'new message', 'body':
                                                              '{[b]}{[font color="blue"]}All{[/font]}{[/b]}{[newline]}Small message to give a big {[u]}kiss{[/u]} ;){[newline]}{[newline]}Bye'}, False)
        self.factory.xfer = MessageValidRecipient()
        self.calljson('/lucterios.mailing/messageValidRecipient',
                      {'message': '1', 'modelname': 'contacts.Individual', 'CRITERIA': 'genre||8||1'}, False)
        self.factory.xfer = MessageValidRecipient()
        self.calljson('/lucterios.mailing/messageValidRecipient',
                      {'message': '1', 'modelname': 'contacts.LegalEntity', 'CRITERIA': ''}, False)
        self.factory.xfer = MessageTransition()
        self.calljson('/lucterios.mailing/messageTransition', {'message': '1', 'TRANSITION': 'valid', 'CONFIRME': 'YES'}, False)
        self.assert_observer('core.acknowledge', 'lucterios.mailing', 'messageTransition')

        self.factory.xfer = MessageLetter()
        self.calljson('/lucterios.mailing/messageLetter', {'message': '1'}, False)
        self.assert_observer('core.custom', 'lucterios.mailing', 'messageLetter')
        self.assert_json_equal('SELECT', "MODEL", '5')

        self.factory.xfer = MessageLetter()
        self.calljson('/lucterios.mailing/messageLetter',
                      {'message': '1', 'PRINT_MODE': '3', 'MODEL': 5}, False)
        self.assert_observer('core.print', 'lucterios.mailing', 'messageLetter')
        pdf_value = b64decode(six.text_type(self.response_json['print']["content"]))
        self.assertEqual(pdf_value[:4], "%PDF".encode('ascii', 'ignore'))

    def test_manage_docs(self):
        self.factory.user = LucteriosUser.objects.create(username='empty')
        self.factory.user.is_superuser = True
        self.factory.user.save()

        create_doc(self.factory.user, with_folder=False)
        self.factory.xfer = MessageAddModify()
        self.calljson('/lucterios.mailing/messageAddModify', {'SAVE': 'YES', 'subject': 'new message', 'body':
                                                              '{[b]}{[font color="blue"]}All{[/font]}{[/b]}{[newline]}Small message to give a big {[u]}kiss{[/u]} ;){[newline]}{[newline]}Bye'}, False)

        self.factory.xfer = MessageShow()
        self.calljson('/lucterios.mailing/messageShow', {'message': '1'}, False)
        self.assert_observer('core.custom', 'lucterios.mailing', 'messageShow')
        self.assert_count_equal('', 10)
        self.assert_json_equal('LABELFORM', "status", 'ouvert')
        self.assert_grid_equal('document', {"name": 'nom', "description": 'description', "date_modification": 'date de modification'}, 0)
        self.assert_count_equal("#document/actions", 3)

        self.factory.xfer = MessageInsertDoc()
        self.calljson('/lucterios.mailing/messageInsertDoc', {'message': '1'}, False)
        self.assert_observer('core.custom', 'lucterios.mailing', 'messageInsertDoc')
        self.assert_count_equal("document", 3)
        self.assert_count_equal("#document/actions", 4)
        self.assert_action_equal("#document/actions/@0", ('Sélection', 'images/ok.png', 'lucterios.mailing', 'messageValidInsertDoc', 1, 1, 0))

        self.factory.xfer = MessageValidInsertDoc()
        self.calljson('/lucterios.mailing/messageValidInsertDoc', {'message': '1', 'document': '1'}, False)
        self.assert_observer('core.acknowledge', 'lucterios.mailing', 'messageValidInsertDoc')
        self.factory.xfer = MessageValidInsertDoc()
        self.calljson('/lucterios.mailing/messageValidInsertDoc', {'message': '1', 'document': '3'}, False)
        self.assert_observer('core.acknowledge', 'lucterios.mailing', 'messageValidInsertDoc')

        self.factory.xfer = MessageShow()
        self.calljson('/lucterios.mailing/messageShow', {'message': '1'}, False)
        self.assert_observer('core.custom', 'lucterios.mailing', 'messageShow')
        self.assert_count_equal('', 10)
        self.assert_json_equal('LABELFORM', "status", 'ouvert')
        self.assert_count_equal("document", 2)
        self.assert_count_equal("#document/actions", 3)
        self.assertEqual(len(self.json_actions), 2)

        self.factory.xfer = MessageRemoveDoc()
        self.calljson('/lucterios.mailing/messageRemoveDoc',
                      {'message': '1', 'document': '1;2', 'CONFIRME': 'YES'}, False)
        self.assert_observer('core.acknowledge', 'lucterios.mailing', 'messageRemoveDoc')

        self.factory.xfer = MessageValidRecipient()
        self.calljson('/lucterios.mailing/messageValidRecipient',
                      {'message': '1', 'modelname': 'contacts.LegalEntity', 'CRITERIA': ''}, False)

        self.factory.xfer = MessageShow()
        self.calljson('/lucterios.mailing/messageShow', {'message': '1'}, False)
        self.assert_observer('core.custom', 'lucterios.mailing', 'messageShow')
        self.assert_count_equal('', 11)
        self.assert_json_equal('LABELFORM', "status", 'ouvert')
        self.assert_count_equal("document", 1)
        self.assert_count_equal("#document/actions", 3)
        self.assertEqual(len(self.json_actions), 3)

        self.factory.xfer = MessageTransition()
        self.calljson('/lucterios.mailing/messageTransition', {'message': '1', 'TRANSITION': 'valid', 'CONFIRME': 'YES'}, False)
        self.assert_observer('core.acknowledge', 'lucterios.mailing', 'messageTransition')

        self.factory.xfer = MessageShow()
        self.calljson('/lucterios.mailing/messageShow', {'message': '1'}, False)
        self.assert_observer('core.custom', 'lucterios.mailing', 'messageShow')
        self.assert_count_equal('', 11)
        self.assert_json_equal('LABELFORM', "status", 'validé')
        self.assert_count_equal("document", 1)
        self.assert_count_equal("#document/actions", 1)


class SendMailingTest(AsychronousLucteriosTest):

    def setUp(self):
        LucteriosTest.setUp(self)
        change_ourdetail()
        create_jack(firstname="jack", lastname='Dalton')
        create_jack(firstname="joe", lastname='Dalton')
        create_jack(firstname="wiliam", lastname='Dalton')
        create_jack(firstname="avrel", lastname='Dalton')
        contact_luke = create_jack(firstname="lucky", lastname='Luke')
        contact_luke.email += ';lucky@luke.org,luke@usmarchal.gov'
        contact_luke.save()
        create_jack(firstname="émilie", lastname='Jolie')
        create_jack(firstname="jean", lastname="Valjean", with_email=False)
        create_jack(firstname="joe", lastname='Lindien')
        create_doc(LucteriosUser.objects.get(username='admin'), with_folder=False)

    def test(self):
        self.calljson('/CORE/authentification', {'username': 'admin', 'password': 'admin'})
        self.assert_observer('core.auth', 'CORE', 'authentification')
        self.assert_json_equal('', '', 'OK')

        configSMTP('localhost', 1025, batchtime=0.1, batchsize=4)
        self.calljson('/lucterios.mailing/messageAddModify', {'SAVE': 'YES', 'subject': 'new message', 'body':
                                                              '{[b]}{[font color="blue"]}All{[/font]}{[/b]}{[newline]}Small message to give a big {[u]}kiss{[/u]} ;){[newline]}{[newline]}Bye'})
        self.calljson('/lucterios.mailing/messageValidRecipient', {'message': '1', 'modelname': 'contacts.Individual', 'CRITERIA': 'genre||8||1'})
        self.calljson('/lucterios.mailing/messageValidRecipient', {'message': '1', 'modelname': 'contacts.LegalEntity', 'CRITERIA': ''})
        self.calljson('/lucterios.mailing/messageValidInsertDoc', {'message': '1', 'document': '1'})
        self.calljson('/lucterios.mailing/messageValidInsertDoc', {'message': '1', 'document': '3'})
        self.calljson('/lucterios.mailing/messageTransition', {'message': '1', 'TRANSITION': 'valid', 'CONFIRME': 'YES'})
        server = TestReceiver()
        server.start(1025)
        try:
            self.assertEqual(0, server.count())
            self.calljson('/lucterios.mailing/messageTransition', {'message': '1', 'TRANSITION': 'sending', 'CONFIRME': 'YES'})
            self.assertEqual(0, server.count())
            sleep(10)
            self.assertEqual(1, len(LucteriosScheduler.get_list()))
            sleep(20)
            self.assertEqual(8, server.count())
            self.assertEqual(0, len(LucteriosScheduler.get_list()))
            self.assertEqual('mr-sylvestre@worldcompany.com', server.get(0)[1])
            self.assertEqual(['mr-sylvestre@worldcompany.com'], server.get(0)[2])
            msg, msg_file1, msg_file3 = server.check_first_message('new message', 3)
            self.assertEqual('text/html', msg.get_content_type())
            self.assertEqual('base64', msg.get('Content-Transfer-Encoding', ''))
            self.assertEqual(
                '<html><body><b><font color="blue">All</font></b><br/>Small message to give a big <u>kiss</u> ;)<br/><br/>Bye</body></html>', decode_b64(msg.get_payload()))
            self.assertTrue('doc1.png' in msg_file1.get('Content-Type', ''), msg_file1.get('Content-Type', ''))
            content_msg1 = b64decode(msg_file1.get_payload())
            self.assertEqual(b"\x89PNG", content_msg1[:4])
            self.assertEqual(4054, len(content_msg1))
            self.assertTrue('doc3.png' in msg_file3.get('Content-Type', ''), msg_file3.get('Content-Type', ''))
            content_msg3 = b64decode(msg_file3.get_payload())
            self.assertEqual(b"\x89PNG", content_msg3[:4])
            self.assertEqual(3774, len(content_msg3))
        finally:
            server.stop()

        self.calljson('/lucterios.mailing/messageSentInfo', {'message': '1', 'show_only_failed': False})
        self.assert_observer('core.custom', 'lucterios.mailing', 'messageSentInfo')
        self.assert_count_equal('', 6)
        self.assert_grid_equal('emailsent', {"contact": "contact", "email": "courriel", "date": "date", "success": "succès"}, 9)
        self.assert_json_equal('', "emailsent/@0/email", "mr-sylvestre@worldcompany.com")
        self.assert_json_equal('', "emailsent/@0/success", 1)
        self.assert_json_equal('', "emailsent/@1/email", "jack@worldcompany.com")
        self.assert_json_equal('', "emailsent/@1/success", 1)
        self.assert_json_equal('', "emailsent/@2/email", "joe@worldcompany.com")
        self.assert_json_equal('', "emailsent/@2/success", 1)
        self.assert_json_equal('', "emailsent/@3/email", "wiliam@worldcompany.com")
        self.assert_json_equal('', "emailsent/@3/success", 1)
        self.assert_json_equal('', "emailsent/@4/email", "avrel@worldcompany.com")
        self.assert_json_equal('', "emailsent/@4/success", 1)
        self.assert_json_equal('', "emailsent/@5/email", "lucky@worldcompany.com")
        self.assert_json_equal('', "emailsent/@5/success", 1)
        self.assert_json_equal('', "emailsent/@6/email", "lucky@luke.org")
        self.assert_json_equal('', "emailsent/@6/success", 1)
        self.assert_json_equal('', "emailsent/@7/email", "luke@usmarchal.gov")
        self.assert_json_equal('', "emailsent/@7/success", 1)
        self.assert_json_equal('', "emailsent/@8/email", "émilie@worldcompany.com")
        self.assert_json_equal('', "emailsent/@8/success", 0)
        self.assertEqual(len(self.json_actions), 1)

        self.calljson('/lucterios.mailing/messageSentInfo', {'message': '1', 'show_only_failed': True})
        self.assert_observer('core.custom', 'lucterios.mailing', 'messageSentInfo')
        self.assert_count_equal('', 6)
        self.assert_grid_equal('emailsent', {"contact": "contact", "email": "courriel", "date": "date", "success": "succès", "error": "erreur"}, 1)
        self.assert_json_equal('', "emailsent/@0/email", "émilie@worldcompany.com")
        self.assert_json_equal('', "emailsent/@0/success", 0)
        self.assert_json_equal('', "emailsent/@0/error", "'ascii' codec can't encode character", True)


class UserTest(LucteriosTest):

    def setUp(self):
        LucteriosTest.setUp(self)
        self.factory.user = AnonymousUser()
        change_ourdetail()
        create_jack(LucteriosUser.objects.create(first_name='jack', last_name='MISTER', username='jack', email='jack@worldcompany.com'))

    def test_pwd_forget(self):
        configSMTP('localhost', 1025)
        self.factory.xfer = AskPassword()
        self.calljson('/CORE/askPassword', {}, False)
        self.assert_observer('core.custom', 'CORE', 'askPassword')
        self.assertEqual(len(self.json_context), 0)
        self.assertEqual(len(self.json_actions), 2)
        self.assert_count_equal('', 3)
        self.assert_json_equal('EDIT', "email", '')

        server = TestReceiver()
        server.start(1025)
        try:
            self.assertEqual(0, server.count())

            self.factory.xfer = AskPasswordAct()
            self.calljson('/CORE/askPasswordAct', {"email": "inconnu@worldcompany.com"}, False)
            self.assert_observer('core.acknowledge', 'CORE', 'askPasswordAct')
            self.assertEqual(0, server.count())

            self.factory.xfer = AskPasswordAct()
            self.calljson('/CORE/askPasswordAct', {"email": "jack@worldcompany.com"}, False)
            self.assert_observer('core.acknowledge', 'CORE', 'askPasswordAct')
            self.assertEqual(1, server.count())
            self.assertEqual('mr-sylvestre@worldcompany.com', server.get(0)[1])
            self.assertEqual(['jack@worldcompany.com'], server.get(0)[2])
            msg, = server.check_first_message('Mot de passe de connexion', 1)
            self.assertEqual('text/html', msg.get_content_type())
            self.assertEqual('base64', msg.get('Content-Transfer-Encoding', ''))
            message = decode_b64(msg.get_payload())
            self.assertEqual('<html>Bienvenue<br/><br/>Confirmation de connexion à votre application :'
                             '<br/> - Alias : jack<br/> - Mot de passe : ', message[:115])
            password = message[115:].split('<br/>')[0]
        finally:
            server.stop()
        user = LucteriosUser.objects.get(id=2)
        self.assertTrue(user.check_password(password), 'success after change:%s (%s)' % (password, message[100:130]))

    def test_no_new_account(self):
        self.factory.xfer = CreateAccount()
        self.calljson('/lucterios.contacts/createAccount', {}, False)
        self.assert_observer('core.exception', 'lucterios.contacts', 'createAccount')

    def test_new_account(self):
        param = Parameter.objects.get(name='contacts-createaccount')
        param.value = '1'
        param.save()
        configSMTP('localhost', 1025)

        self.factory.xfer = CreateAccount()
        self.calljson('/lucterios.contacts/createAccount', {}, False)
        self.assert_observer('core.custom', 'lucterios.contacts', 'createAccount')
        self.assertEqual(len(self.json_context), 0)
        self.assertEqual(len(self.json_actions), 2)
        self.assert_count_equal('', 8)
        self.assert_json_equal('SELECT', "genre", '1')
        self.assert_json_equal('EDIT', "firstname", '')
        self.assert_json_equal('EDIT', "lastname", '')
        self.assert_json_equal('EDIT', "username", '')
        self.assert_json_equal('EDIT', "email", '')
        self.assert_json_equal('CAPTCHA', "captcha", '')

        server = TestReceiver()
        server.start(1025)
        try:
            self.factory.xfer = CreateAccount()
            self.calljson('/lucterios.contacts/createAccount', {'SAVE': 'YES', 'firstname': 'pierre', 'genre': 1,
                                                                'lastname': 'DUPONT', 'username': 'admin', 'email': 'pierre@worldcompany.com'}, False)
            self.assert_observer('core.acknowledge', 'lucterios.contacts', 'createAccount')
            self.assertEqual(len(self.json_context), 6)
            self.assert_action_equal(self.response_json['action'], ('', None, 'lucterios.contacts', 'createAccount', 1, 1, 1, {
                                     "SAVE": '', "error": "Ce compte existe déjà !"}))
            self.assertEqual(0, server.count())

            self.factory.xfer = CreateAccount()
            self.calljson('/lucterios.contacts/createAccount', {'SAVE': 'YES', 'firstname': 'pierre', 'genre': 1,
                                                                'lastname': 'DUPONT', 'username': 'pierre', 'email': 'pierre@worldcompany.com'}, False)
            self.assert_observer('core.dialogbox', 'lucterios.contacts', 'createAccount')
            self.assert_json_equal('', 'text', 'Votre compte est créé{[br/]}Vous allez recevoir un courriel avec votre mot de passe.')
            self.assertEqual(1, server.count())
            self.assertEqual('mr-sylvestre@worldcompany.com', server.get(0)[1])
            self.assertEqual(['pierre@worldcompany.com'], server.get(0)[2])
            msg, = server.check_first_message('Mot de passe de connexion', 1)
            self.assertEqual('text/html', msg.get_content_type())
            self.assertEqual('base64', msg.get('Content-Transfer-Encoding', ''))
            message = decode_b64(msg.get_payload())
            self.assertEqual('<html>Bienvenue<br/><br/>Confirmation de connexion à votre application :'
                             '<br/> - Alias : pierre<br/> - Mot de passe : ', message[:117])
            password = message[117:].split('<br/>')[0]
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
        self.calljson('/lucterios.contacts/createAccount', {}, False)
        self.assert_observer('core.custom', 'lucterios.contacts', 'createAccount')
        self.assertEqual(len(self.json_context), 0)
        self.assertEqual(len(self.json_actions), 2)
        self.assert_count_equal('', 9)
        self.assert_json_equal('SELECT', "genre", '1')
        self.assert_json_equal('EDIT', "firstname", '')
        self.assert_json_equal('EDIT', "lastname", '')
        self.assert_json_equal('EDIT', "username", '')
        self.assert_json_equal('EDIT', "email", '')
        self.assert_json_equal('EDIT', "legalentity", '')
        self.assert_json_equal('CAPTCHA', "captcha", '')

        server = TestReceiver()
        server.start(1025)
        try:
            self.factory.xfer = CreateAccount()
            self.calljson('/lucterios.contacts/createAccount', {'SAVE': 'YES', 'firstname': 'pierre', 'genre': 1, 'legalentity': 'Chez moi',
                                                                'lastname': 'DUPONT', 'username': 'pierre', 'email': 'pierre@worldcompany.com'}, False)
            self.assert_observer('core.dialogbox', 'lucterios.contacts', 'createAccount')
            self.assert_json_equal('', 'text', 'Votre compte est créé{[br/]}Vous allez recevoir un courriel avec votre mot de passe.')
            self.assertEqual(1, server.count())
            self.assertEqual('mr-sylvestre@worldcompany.com', server.get(0)[1])
            self.assertEqual(['pierre@worldcompany.com'], server.get(0)[2])
            msg, = server.check_first_message('Mot de passe de connexion', 1)
            self.assertEqual('text/html', msg.get_content_type())
            self.assertEqual('base64', msg.get('Content-Transfer-Encoding', ''))
            message = decode_b64(msg.get_payload())
            self.assertEqual('<html>Bienvenue<br/><br/>Confirmation de connexion à votre application :'
                             '<br/> - Alias : pierre<br/> - Mot de passe : ', message[:117])
            password = message[117:].split('<br/>')[0]
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
