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
from email.header import decode_header

from django.utils import six
from django.contrib.auth.models import AnonymousUser

from lucterios.framework.test import LucteriosTest, AsychronousLucteriosTest
from lucterios.framework.filetools import get_user_dir
from lucterios.framework.error import LucteriosException
from lucterios.framework.tools import get_binay
from lucterios.framework.models import LucteriosScheduler
from lucterios.CORE.models import Parameter, LucteriosUser, PrintModel
from lucterios.CORE.views_usergroup import UsersEdit
from lucterios.CORE.views import AskPassword, AskPasswordAct

from lucterios.contacts.tests_contacts import change_ourdetail, create_jack
from lucterios.contacts.views import CreateAccount
from lucterios.contacts.models import Individual, LegalEntity

from lucterios.mailing.views import Configuration, SendEmailTry
from lucterios.mailing.functions import will_mail_send, send_email
from lucterios.mailing.views_message import MessageAddModify, MessageList, MessageDel, MessageShow, MessageValidRecipient,\
    MessageDelRecipient, MessageLetter, MessageTransition, MessageInsertDoc,\
    MessageValidInsertDoc, MessageRemoveDoc, MessageSendEmailTry
from lucterios.mailing.test_tools import configSMTP, decode_b64, TestReceiver

from lucterios.documents.tests import create_doc
from lucterios.documents.models import DocumentContainer
from lucterios.mailing.models import Message


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
        self.assert_count_equal('', 2 + 10 + 2 + 2)
        self.assert_json_equal('LABELFORM', "mailing-smtpserver", '')
        self.assert_json_equal('LABELFORM', "mailing-smtpport", '25')
        self.assert_json_equal('LABELFORM', "mailing-smtpsecurity", 'Aucune')
        self.assert_json_equal('LABELFORM', "mailing-smtpuser", '')
        self.assert_json_equal('LABELFORM', "mailing-smtppass", '')
        self.assert_json_equal('LABELFORM', "mailing-dkim-private-path", '')
        self.assert_json_equal('LABELFORM', "mailing-dkim-selector", 'default')
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
        try:
            from Crypto.PublicKey import RSA
            dkim_private_file = join(get_user_dir(), "private.pem")
            key = RSA.generate(1024)
            pv_key_string = key.export_key()
            with open(dkim_private_file, "wb") as prv_file:
                prv_file.write(pv_key_string)
        except Exception:
            dkim_private_file = ""
        configSMTP('localhost', 1025, dkim_private_file=dkim_private_file)
        self.assertEqual(0, self.server.count())

        self.factory.xfer = SendEmailTry()
        self.calljson('/lucterios.mailing/sendEmailTry', {}, False)
        self.assert_observer('core.custom', 'lucterios.mailing', 'sendEmailTry')
        self.assert_json_equal('EDIT', "recipient", 'mr-sylvestre@worldcompany.com')

        self.factory.xfer = SendEmailTry()
        self.calljson('/lucterios.mailing/sendEmailTry', {'CONFIRME': 'YES', "recipient": 'behoa@worldcompany.com'}, False)
        self.assert_observer('core.dialogbox', 'lucterios.mailing', 'sendEmailTry')
        self.assert_json_equal('', 'text', 'Courriel envoyé, veuillez le vérifier.')

        self.assertEqual(1, self.server.count())
        self.assertEqual('mr-sylvestre@worldcompany.com', self.server.get(0)[1])
        self.assertEqual(['behoa@worldcompany.com'], self.server.get(0)[2])
        msg = self.server.get_first_msg()

        msg_id = decode_header(msg.get('Message-ID'))[0][0]
        self.assertEqual('@worldcompany.com>', msg_id[-18:], msg_id)

        if dkim_private_file != "":
            msg_dkim = decode_header(msg.get('DKIM-Signature'))[0][0]
            self.assertEqual('v=1; a=rsa-sha256; c=relaxed/simple; d=worldcompany.com;', msg_dkim[:56], msg_dkim)
        else:
            six.print_("-- NO DKIM --")

        message, = self.server.check_first_message('Essai de courriel', 1)
        self.assertEqual('text/plain', message.get_content_type())
        self.assertEqual('base64', message.get('Content-Transfer-Encoding', ''))
        self.assertEqual('Courriel envoyé pour vérifier la configuration\n\nWoldCompany\n', decode_b64(message.get_payload())[:60])

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
        msg1, msg2, = self.server.check_first_message('send html', 2)
        self.assertEqual('text/html', msg1.get_content_type())
        self.assertEqual('base64', msg1.get('Content-Transfer-Encoding', ''))
        self.assertEqual('<html><body><h1>Yessss!!!</h1></body></html>', decode_b64(msg1.get_payload()))
        self.assertEqual('text/plain', msg2.get_content_type())
        self.assertEqual('base64', msg2.get('Content-Transfer-Encoding', ''))
        self.assertEqual('# Yessss!!!\n\n', decode_b64(msg2.get_payload()))

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
            self.assertTrue(('unknown protocol' in six.text_type(error)) or ('SSL: WRONG_VERSION_NUMBER' in six.text_type(error)), six.text_type(error))
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
        msg, _msg = self.server.check_first_message('Mot de passe de connexion', 2)
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
        self.assert_count_equal('', 4)

        self.factory.xfer = MessageAddModify()
        self.calljson('/lucterios.mailing/messageAddModify', {'SAVE': 'YES', 'doc_in_link': 0, 'subject': 'new message', 'body':
                                                              '{[b]}{[font color="blue"]}All{[/font]}{[/b]}{[newline]}Small message to give a big {[u]}kiss{[/u]} ;){[newline]}{[newline]}Bye'}, False)
        self.assert_observer('core.acknowledge', 'lucterios.mailing', 'messageAddModify')

        self.factory.xfer = MessageList()
        self.calljson('/lucterios.mailing/messageList', {}, False)
        self.assert_observer('core.custom', 'lucterios.mailing', 'messageList')
        self.assert_count_equal("message", 1)
        self.assert_json_equal('', "message/@0/status", 0)
        self.assert_json_equal('', "message/@0/date", None)
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
        self.assert_count_equal('', 12)
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
        self.assert_count_equal('', 13)
        self.assertEqual(len(self.json_actions), 3)
        self.assert_action_equal(self.json_actions[0], ('Valider', 'images/transition.png', 'lucterios.mailing', 'messageTransition', 0, 1, 1, {'TRANSITION': 'valid'}))
        self.assert_action_equal(self.json_actions[1], ('Modifier', 'images/edit.png', 'lucterios.mailing', 'messageAddModify', 1, 1, 1))
        self.assert_action_equal(self.json_actions[2], ('Fermer', 'images/close.png'))
        self.assert_json_equal('LABELFORM', "status", 0)
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
        self.assert_count_equal('', 13)
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
        self.assert_count_equal('', 13)
        self.assert_json_equal('LABELFORM', "status", 1)
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
        self.assert_count_equal('', 14)
        self.assert_json_equal('LABELFORM', "contact_noemail", ['Valjean jean'])
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
        self.save_pdf()

    def test_letter_message_html(self):
        html_content = """
{[p]}{[u]}{[b]}{[span style="font-size:24px;"]}Titre{[/span]}{[/b]}{[/u]}{[/p]}
Lorem ipsum dolor sit amet, consectetur adipiscing elit. Tu enim ista lenius, hic Stoicorum more nos vexat.{[br]}
{[i]}Quando enim Socrates, qui parens philosophiae iure dici potest, quicquam tale fecit?{[/i]}{[br]}
{[strike]}Quodsi ipsam honestatem undique pertectam atque absolutam. Duo Reges: constructio interrete.{[/strike]}{[br]}
Quid ad utilitatem tantae pecuniae? Sed nimis multa.{[br]}
{[br]}
Choix:{[br]}
{[ul]}{[li]}{[span style="color:rgb(0,0,255);"]}Bleu{[/span]}{[/li]}{[li]}{[span style="color:rgb(255,0,0);"]}Rouge{[/span]}{[/li]}{[li]}{[span style="color:rgb(255,255,0);"]}Jaune{[/span]}{[/li]}{[/ul]}
{[blockquote]}Multoque hoc melius nos veriusque quam Stoici.{[br]}
Ea possunt paria non esse.{[br]}
Cui Tubuli nomen odio non est?{[br]}
Quamquam tu hanc copiosiorem etiam soles dicere.{[br]}
Ita redarguitur ipse a sese, convincunturque scripta eius probitate ipsius ac moribus.{[br]}
Varietates autem iniurasque fortunae facile veteres philosophorum praeceptis instituta vita superabat.{[br]}
Tum Quintus: Est plane, Piso, ut dicis, inquit. Id est enim, de quo quaerimus.{[br]}
Nec mihi illud dixeris: Haec enim ipsa mihi sunt voluptati, et erant illa Torquatis.{[br]}
Deque his rebus satis multa in nostris de re publica libris sunt dicta a Laelio.{[br]}
{[/blockquote]}{[br]}
{[hr]}
{[p]}{[br]}
{[/p]}
{[p align="left"]}A Gauche{[/p]}
{[p align="center"]}Au Centre{[br]}
{[/p]}
{[p align="right"]}A Droite{[br]}
{[/p]}
{[br]}
{[blockquote]}{[blockquote]}{[b]}Adresse:{[/b]} {[a href="https://www.diacamma.org"]}diacamma.org{[/a]}{[br]}
{[/blockquote]}{[/blockquote]}{[p]}{[br]}
{[/p]}
{[p]}{[i]}Grosses papouille{[/i]}{[/p]}
{[p]}{[/p]}
"""

        self.factory.xfer = MessageAddModify()
        self.calljson('/lucterios.mailing/messageAddModify', {'SAVE': 'YES', 'subject': 'new message', 'body': html_content}, False)
        self.factory.xfer = MessageValidRecipient()
        self.calljson('/lucterios.mailing/messageValidRecipient', {'message': '1', 'modelname': 'contacts.Individual', 'CRITERIA': 'genre||8||1'}, False)
        self.factory.xfer = MessageTransition()
        self.calljson('/lucterios.mailing/messageTransition', {'message': '1', 'TRANSITION': 'valid', 'CONFIRME': 'YES'}, False)

        self.factory.xfer = MessageLetter()
        self.calljson('/lucterios.mailing/messageLetter', {'message': '1', 'PRINT_MODE': '3', 'MODEL': 5}, False)
        self.assert_observer('core.print', 'lucterios.mailing', 'messageLetter')
        self.save_pdf()

    def test_manage_docs(self):
        self.factory.user = LucteriosUser.objects.create(username='empty')
        self.factory.user.is_superuser = True
        self.factory.user.save()

        create_doc(self.factory.user, with_folder=False)
        self.factory.xfer = MessageAddModify()
        self.calljson('/lucterios.mailing/messageAddModify', {'SAVE': 'YES', 'doc_in_link': 0, 'subject': 'new message', 'body':
                                                              '{[b]}{[font color="blue"]}All{[/font]}{[/b]}{[newline]}Small message to give a big {[u]}kiss{[/u]} ;){[newline]}{[newline]}Bye'}, False)

        self.factory.xfer = MessageShow()
        self.calljson('/lucterios.mailing/messageShow', {'message': '1'}, False)
        self.assert_observer('core.custom', 'lucterios.mailing', 'messageShow')
        self.assert_count_equal('', 12)
        self.assert_json_equal('LABELFORM', "status", 0)
        self.assert_grid_equal('attachments', {"name": 'nom', "description": 'description', "date_modification": 'date de modification'}, 0)
        self.assert_json_equal('LABELFORM', "doc_in_link", False)
        self.assert_count_equal("#attachments/actions", 3)

        self.factory.xfer = MessageInsertDoc()
        self.calljson('/lucterios.mailing/messageInsertDoc', {'message': '1'}, False)
        self.assert_observer('core.custom', 'lucterios.mailing', 'messageInsertDoc')
        self.assert_count_equal("document", 3)
        self.assert_count_equal("#document/actions", 3)
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
        self.assert_count_equal('', 12)
        self.assert_json_equal('LABELFORM', "status", 0)
        self.assert_count_equal("attachments", 2)
        self.assert_count_equal("#attachments/actions", 3)
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
        self.assert_count_equal('', 13)
        self.assert_json_equal('LABELFORM', "status", 0)
        self.assert_count_equal("attachments", 1)
        self.assert_count_equal("#attachments/actions", 3)
        self.assertEqual(len(self.json_actions), 3)

        self.factory.xfer = MessageTransition()
        self.calljson('/lucterios.mailing/messageTransition', {'message': '1', 'TRANSITION': 'valid', 'CONFIRME': 'YES'}, False)
        self.assert_observer('core.acknowledge', 'lucterios.mailing', 'messageTransition')

        self.factory.xfer = MessageShow()
        self.calljson('/lucterios.mailing/messageShow', {'message': '1'}, False)
        self.assert_observer('core.custom', 'lucterios.mailing', 'messageShow')
        self.assert_count_equal('', 13)
        self.assert_json_equal('LABELFORM', "status", 1)
        self.assert_count_equal("attachments", 1)
        self.assert_count_equal("#attachments/actions", 1)

    def test_trysend(self):
        configSMTP('', 25)
        self.factory.xfer = MessageAddModify()
        self.calljson('/lucterios.mailing/messageAddModify', {'SAVE': 'YES', 'subject': 'new message', 'body':
                                                              '{[b]}{[font color="blue"]}All{[/font]}{[/b]}{[newline]}Small message to give a big {[u]}kiss{[/u]} ;){[newline]}{[newline]}Bye'}, False)

        self.factory.xfer = MessageShow()
        self.calljson('/lucterios.mailing/messageShow', {'message': '1'}, False)
        self.assert_observer('core.custom', 'lucterios.mailing', 'messageShow')
        self.assertEqual(len(self.json_actions), 2)

        configSMTP('localhost', 1025)
        self.factory.xfer = MessageShow()
        self.calljson('/lucterios.mailing/messageShow', {'message': '1'}, False)
        self.assert_observer('core.custom', 'lucterios.mailing', 'messageShow')
        self.assertEqual(len(self.json_actions), 3)

        server = TestReceiver()
        server.start(1025)
        try:
            self.assertEqual(0, server.count())
            self.factory.xfer = MessageSendEmailTry()
            self.calljson('/lucterios.mailing/messageSendEmailTry', {'message': '1'}, False)
            self.assert_observer('core.custom', 'lucterios.mailing', 'messageSendEmailTry')
            self.assert_json_equal('EDIT', "recipient", 'mr-sylvestre@worldcompany.com')

            self.factory.xfer = MessageSendEmailTry()
            self.calljson('/lucterios.mailing/messageSendEmailTry', {'message': '1', 'CONFIRME': 'YES', "recipient": 'behoa@worldcompany.com'}, False)
            self.assert_observer('core.dialogbox', 'lucterios.mailing', 'messageSendEmailTry')
            self.assert_json_equal('', 'text', 'Courriel envoyé, veuillez le vérifier.')

            self.assertEqual(1, server.count())
            self.assertEqual('mr-sylvestre@worldcompany.com', server.get(0)[1])
            self.assertEqual(['behoa@worldcompany.com'], server.get(0)[2])
        finally:
            server.stop()

    def test_send_classic(self):
        self.factory.user = LucteriosUser.objects.create(username='empty')
        self.factory.user.is_superuser = True
        self.factory.user.save()
        create_doc(self.factory.user, with_folder=False)

        configSMTP('localhost', 1025)
        server = TestReceiver()
        server.start(1025)
        try:
            email_msg = Message.objects.create(subject="Sending '#reference'", body="{[b]}#name{[/b]}{[br/]}{[br/]}With Document: {[i]}#doc{[/i]}{[br/]}{[br/]}Bye")
            email_msg.add_recipient('contacts.Individual', 'genre||8||1')
            email_msg.add_recipient('contacts.LegalEntity', '')
            email_msg.save()
            email_msg.attachments.add(DocumentContainer.objects.get(id=1))
            email_msg.valid()
            self.assertEqual(3, email_msg.contact_nb)
            self.assertEqual(['Valjean jean'], email_msg.contact_noemail)
            email_msg._prep_sending()
            email_msg.status = 2
            email_msg.save()
            self.assertEqual(0, server.count())

            email_msg.sendemail(10, "http://testserver")
            self.assertEqual(2, server.count())
            self.assertEqual('mr-sylvestre@worldcompany.com', server.get(0)[1])
            self.assertEqual(['jack@worldcompany.com'], server.get(0)[2])
            self.assertEqual('mr-sylvestre@worldcompany.com', server.get(1)[1])
            self.assertEqual(['mr-sylvestre@worldcompany.com'], server.get(1)[2])

            msg, msg_txt, msg_file1 = server.get_msg_index(1, "Sending ''")

            self.assertEqual('text/html', msg.get_content_type())
            self.assertEqual('base64', msg.get('Content-Transfer-Encoding', ''))
            self.assertEqual("<html><body><b>WoldCompany</b><br/><br/>With Document: <i>doc1.png</i><br/><br/>Bye<img src='http://testserver/lucterios.mailing/emailSentAddForStatistic?emailsent=2' alt=''/></body></html>",
                             decode_b64(msg.get_payload()))

            self.assertEqual('text/plain', msg_txt.get_content_type())
            self.assertEqual('base64', msg_txt.get('Content-Transfer-Encoding', ''))
            self.assertEqual('**WoldCompany**  \n  \nWith Document: _doc1.png_  \n  \nBye\n\n', decode_b64(msg_txt.get_payload()))

            self.assertTrue('doc1.png' in msg_file1.get('Content-Type', ''), msg_file1.get('Content-Type', ''))
        finally:
            server.stop()

    def test_send_dynamic(self):

        print_model = PrintModel.objects.create(name="Report", kind="2", modelname="contacts.Individual")
        print_model.value = """
<model hmargin="10.0" vmargin="10.0" page_width="210.0" page_height="297.0">
<header extent="0.0"/>
<bottom extent="0.0"/>
<body>
<text height="8.0" width="190.0" top="0.0" left="0.0" padding="1.0" spacing="0.0" border_color="black" border_style="" border_width="0.2" text_align="center" line_height="15" font_family="sans-serif" font_weight="" font_size="15">
{[b]}#firstname #lastname{[/b]}
</text>
</body>
</model>
"""
        print_model.save()

        create_jack(firstname="jack", lastname='Dalton')
        create_jack(firstname="joe", lastname='Dalton')
        create_jack(firstname="wiliam", lastname='Dalton')
        create_jack(firstname="avrel", lastname='Dalton')

        configSMTP('localhost', 1025)
        server = TestReceiver()
        server.start(1025)
        try:
            email_msg = Message.objects.create(subject="Sending '#reference'", body="{[b]}#name{[/b]}{[br/]}{[br/]}With Document: {[i]}#doc{[/i]}{[br/]}{[br/]}Bye",
                                               email_to_send="contacts.Individual:0:%d" % print_model.id)
            email_msg.add_recipient('contacts.Individual', 'id||8||4;5;6;7')
            email_msg.save()
            email_msg.valid()
            self.assertEqual(4, email_msg.contact_nb)
            self.assertEqual([], email_msg.contact_noemail)
            email_msg._prep_sending()
            email_msg.status = 2
            email_msg.save()
            self.assertEqual(0, server.count())

            email_msg.sendemail(10, "http://testserver")
            self.assertEqual(4, server.count())
            self.assertEqual('mr-sylvestre@worldcompany.com', server.get(0)[1])
            self.assertEqual(['avrel@worldcompany.com', 'mr-sylvestre@worldcompany.com'], server.get(0)[2])
            self.assertEqual('mr-sylvestre@worldcompany.com', server.get(1)[1])
            self.assertEqual(['jack@worldcompany.com', 'mr-sylvestre@worldcompany.com'], server.get(1)[2])
            self.assertEqual('mr-sylvestre@worldcompany.com', server.get(2)[1])
            self.assertEqual(['joe@worldcompany.com', 'mr-sylvestre@worldcompany.com'], server.get(2)[2])
            self.assertEqual('mr-sylvestre@worldcompany.com', server.get(3)[1])
            self.assertEqual(['wiliam@worldcompany.com', 'mr-sylvestre@worldcompany.com'], server.get(3)[2])

            msg, msg_txt, msg_file1 = server.get_msg_index(2, "Sending '5'")

            self.assertEqual('text/html', msg.get_content_type())
            self.assertEqual('base64', msg.get('Content-Transfer-Encoding', ''))
            self.assertEqual("<html><body><b>joe Dalton</b><br/><br/>With Document: <i>Report.pdf</i><br/><br/>Bye<img src='http://testserver/lucterios.mailing/emailSentAddForStatistic?emailsent=3' alt=''/></body></html>",
                             decode_b64(msg.get_payload()))

            self.assertEqual('text/plain', msg_txt.get_content_type())
            self.assertEqual('base64', msg_txt.get('Content-Transfer-Encoding', ''))
            self.assertEqual('**joe Dalton**  \n  \nWith Document: _Report.pdf_  \n  \nBye\n\n', decode_b64(msg_txt.get_payload()))

            self.assertTrue('Report.pdf' in msg_file1.get('Content-Type', ''), msg_file1.get('Content-Type', ''))
            for msg_index in range(4):
                _msg, _msg_txt, msg_file = server.get_msg_index(msg_index)
                self.save_pdf(base64_content=msg_file.get_payload(), ident=msg_index + 1)
        finally:
            server.stop()


class SendMailingTest(AsychronousLucteriosTest):

    def setUp(self):
        AsychronousLucteriosTest.setUp(self)
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
        self.calljson('/lucterios.mailing/messageAddModify', {'SAVE': 'YES', 'doc_in_link': 0, 'subject': 'new message', 'body':
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
            self.assertEqual(['avrel@worldcompany.com'], server.get(0)[2])
            msg, msg_txt, msg_file1, msg_file3 = server.check_first_message('new message', 4)
            self.assertEqual('text/html', msg.get_content_type())
            self.assertEqual('base64', msg.get('Content-Transfer-Encoding', ''))
            self.assertEqual(
                "<html><body><b><font color=\"blue\">All</font></b><br/>Small message to give a big <u>kiss</u> ;)<br/><br/>Bye<img src='http://testserver/lucterios.mailing/emailSentAddForStatistic?emailsent=1' alt=''/></body></html>", decode_b64(msg.get_payload()))
            self.assertEqual('text/plain', msg_txt.get_content_type())
            self.assertEqual("**All**  \nSmall message to give a big _kiss_ ;)  \n  \nBye\n\n", decode_b64(msg_txt.get_payload()))

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
        self.assert_count_equal('', 7)
        self.assert_grid_equal('emailsent', {"contact": "contact", "sended_item": "ref. d'envoie", "date": "date", "success": "succès",
                                             "last_open_date": "date de dernière ouverture", "nb_open": "nombre de messages ouverts"}, 9)
        self.assert_json_equal('', "emailsent/@0/sended_item", "mr-sylvestre@worldcompany.com")
        self.assert_json_equal('', "emailsent/@0/success", 1)
        self.assert_json_equal('', "emailsent/@0/nb_open", 0)
        self.assert_json_equal('', "emailsent/@0/id", 9)
        self.assert_json_equal('', "emailsent/@1/sended_item", "jack@worldcompany.com")
        self.assert_json_equal('', "emailsent/@1/success", 1)
        self.assert_json_equal('', "emailsent/@1/nb_open", 0)
        self.assert_json_equal('', "emailsent/@1/id", 2)
        self.assert_json_equal('', "emailsent/@2/sended_item", "joe@worldcompany.com")
        self.assert_json_equal('', "emailsent/@2/success", 1)
        self.assert_json_equal('', "emailsent/@2/nb_open", 0)
        self.assert_json_equal('', "emailsent/@2/id", 3)
        self.assert_json_equal('', "emailsent/@3/sended_item", "wiliam@worldcompany.com")
        self.assert_json_equal('', "emailsent/@3/success", 1)
        self.assert_json_equal('', "emailsent/@3/nb_open", 0)
        self.assert_json_equal('', "emailsent/@3/id", 4)
        self.assert_json_equal('', "emailsent/@4/sended_item", "avrel@worldcompany.com")
        self.assert_json_equal('', "emailsent/@4/success", 1)
        self.assert_json_equal('', "emailsent/@4/nb_open", 0)
        self.assert_json_equal('', "emailsent/@4/id", 1)
        self.assert_json_equal('', "emailsent/@5/sended_item", "luke@usmarchal.gov")
        self.assert_json_equal('', "emailsent/@5/success", 1)
        self.assert_json_equal('', "emailsent/@5/nb_open", 0)
        self.assert_json_equal('', "emailsent/@5/id", 8)
        self.assert_json_equal('', "emailsent/@6/sended_item", "lucky@luke.org")
        self.assert_json_equal('', "emailsent/@6/success", 1)
        self.assert_json_equal('', "emailsent/@6/nb_open", 0)
        self.assert_json_equal('', "emailsent/@6/id", 7)
        self.assert_json_equal('', "emailsent/@7/sended_item", "lucky@worldcompany.com")
        self.assert_json_equal('', "emailsent/@7/success", 1)
        self.assert_json_equal('', "emailsent/@7/nb_open", 0)
        self.assert_json_equal('', "emailsent/@7/id", 6)
        self.assert_json_equal('', "emailsent/@8/sended_item", "émilie@worldcompany.com")
        self.assert_json_equal('', "emailsent/@8/success", 0)
        self.assert_json_equal('', "emailsent/@8/nb_open", 0)
        self.assert_json_equal('', "emailsent/@8/id", 5)

        self.assertEqual(len(self.json_actions), 1)

        self.call_ex('/lucterios.mailing/emailSentAddForStatistic', {'emailsent': '1'}, True)
        self.call_ex('/lucterios.mailing/emailSentAddForStatistic', {'emailsent': '2'}, True)
        self.call_ex('/lucterios.mailing/emailSentAddForStatistic', {'emailsent': '3'}, True)
        self.call_ex('/lucterios.mailing/emailSentAddForStatistic', {'emailsent': '2'}, True)
        self.call_ex('/lucterios.mailing/emailSentAddForStatistic', {'emailsent': '2'}, True)
        self.call_ex('/lucterios.mailing/emailSentAddForStatistic', {'emailsent': '20'}, True)
        self.call_ex('/lucterios.mailing/emailSentAddForStatistic', {}, True)
        self.call_ex('/lucterios.mailing/emailSentAddForStatistic', {'emailsent': '3'}, True)

        self.calljson('/lucterios.mailing/messageSentInfo', {'message': '1', 'show_only_failed': False})
        self.assert_observer('core.custom', 'lucterios.mailing', 'messageSentInfo')
        self.assert_json_equal('', "emailsent/@0/sended_item", "joe@worldcompany.com")
        self.assert_json_equal('', "emailsent/@0/success", 1)
        self.assert_json_equal('', "emailsent/@0/nb_open", 2)
        self.assert_json_equal('', "emailsent/@0/id", 3)
        self.assert_json_equal('', "emailsent/@1/sended_item", "jack@worldcompany.com")
        self.assert_json_equal('', "emailsent/@1/success", 1)
        self.assert_json_equal('', "emailsent/@1/nb_open", 3)
        self.assert_json_equal('', "emailsent/@1/id", 2)
        self.assert_json_equal('', "emailsent/@2/sended_item", "avrel@worldcompany.com")
        self.assert_json_equal('', "emailsent/@2/success", 1)
        self.assert_json_equal('', "emailsent/@2/nb_open", 1)
        self.assert_json_equal('', "emailsent/@2/id", 1)
        self.assert_json_equal('', "emailsent/@3/sended_item", "mr-sylvestre@worldcompany.com")
        self.assert_json_equal('', "emailsent/@3/success", 1)
        self.assert_json_equal('', "emailsent/@3/nb_open", 0)
        self.assert_json_equal('', "emailsent/@3/id", 9)
        self.assert_json_equal('', "emailsent/@4/sended_item", "wiliam@worldcompany.com")
        self.assert_json_equal('', "emailsent/@4/success", 1)
        self.assert_json_equal('', "emailsent/@4/nb_open", 0)
        self.assert_json_equal('', "emailsent/@4/id", 4)
        self.assert_json_equal('', "emailsent/@5/sended_item", "luke@usmarchal.gov")
        self.assert_json_equal('', "emailsent/@5/success", 1)
        self.assert_json_equal('', "emailsent/@5/nb_open", 0)
        self.assert_json_equal('', "emailsent/@5/id", 8)
        self.assert_json_equal('', "emailsent/@6/sended_item", "lucky@luke.org")
        self.assert_json_equal('', "emailsent/@6/success", 1)
        self.assert_json_equal('', "emailsent/@6/nb_open", 0)
        self.assert_json_equal('', "emailsent/@6/id", 7)
        self.assert_json_equal('', "emailsent/@7/sended_item", "lucky@worldcompany.com")
        self.assert_json_equal('', "emailsent/@7/success", 1)
        self.assert_json_equal('', "emailsent/@7/nb_open", 0)
        self.assert_json_equal('', "emailsent/@7/id", 6)
        self.assert_json_equal('', "emailsent/@8/sended_item", "émilie@worldcompany.com")
        self.assert_json_equal('', "emailsent/@8/success", 0)
        self.assert_json_equal('', "emailsent/@8/nb_open", 0)
        self.assert_json_equal('', "emailsent/@8/id", 5)

        val_stat = self.get_json_path("statistic")
        self.assertIn("9 message(s) envoyé(s) le", val_stat)
        self.assertIn("(dont 1 en erreur)", val_stat)
        self.assertIn("Avec 3 message(s) ouvert(s)", val_stat)
        self.assertIn("taux de 33.3 % d'ouverture.", val_stat)

        self.calljson('/lucterios.mailing/messageSentInfo', {'message': '1', 'show_only_failed': True})
        self.assert_observer('core.custom', 'lucterios.mailing', 'messageSentInfo')
        self.assert_count_equal('', 7)
        self.assert_grid_equal('emailsent', {"contact": "contact", "sended_item": "ref. d'envoie", "date": "date", "success": "succès", "error": "erreur"}, 1)
        self.assert_json_equal('', "emailsent/@0/sended_item", "émilie@worldcompany.com")
        self.assert_json_equal('', "emailsent/@0/success", 0)
        self.assert_json_equal('', "emailsent/@0/error", "'ascii' codec can't encode character", True)

        self.calljson('/lucterios.mailing/messageAddModify', {'SAVE': 'YES', 'doc_in_link': 1, 'subject': 'new message', 'body':
                                                              '{[b]}{[font color="blue"]}All{[/font]}{[/b]}{[newline]}Other message to give a big {[u]}kiss{[/u]} ;){[newline]}{[newline]}Bye'})
        self.calljson('/lucterios.mailing/messageValidRecipient', {'message': '2', 'modelname': 'contacts.LegalEntity', 'CRITERIA': ''})
        self.calljson('/lucterios.mailing/messageValidInsertDoc', {'message': '2', 'document': '1'})
        self.calljson('/lucterios.mailing/messageValidInsertDoc', {'message': '2', 'document': '3'})
        self.calljson('/lucterios.mailing/messageTransition', {'message': '2', 'TRANSITION': 'valid', 'CONFIRME': 'YES'})

        self.calljson('/lucterios.mailing/messageShow', {'message': '2'}, True)
        self.assert_observer('core.custom', 'lucterios.mailing', 'messageShow')
        self.assert_json_equal('LABELFORM', "status", 1)
        self.assert_count_equal("recipient_list", 1)
        self.assert_json_equal('LABELFORM', "contact_nb", '1')

        server = TestReceiver()
        server.start(1025)
        try:
            self.assertEqual(0, server.count())
            self.calljson('/lucterios.mailing/messageTransition', {'message': '2', 'TRANSITION': 'sending', 'CONFIRME': 'YES'})
            self.assertEqual(0, server.count())
            sleep(10)
            self.assertEqual(1, len(LucteriosScheduler.get_list()))
            sleep(10)
            self.assertEqual(0, len(LucteriosScheduler.get_list()))
            self.assertEqual(1, server.count())
            self.assertEqual('mr-sylvestre@worldcompany.com', server.get(0)[1])
            self.assertEqual(['mr-sylvestre@worldcompany.com'], server.get(0)[2])
            msg, msg_txt = server.check_first_message('new message', 2)
            self.assertEqual('text/plain', msg_txt.get_content_type())
            self.assertEqual('text/html', msg.get_content_type())
            self.assertEqual('base64', msg.get('Content-Transfer-Encoding', ''))
            content = decode_b64(msg.get_payload())
            self.assertEqual('<html><body><b><font color="blue">All</font></b><br/>Other message to give a big <u>kiss</u> ;)<br/><br/>Bye', content[:108])
            self.assertEqual(content[108:].count('http://testserver/lucterios.documents/downloadFile?shared='), 2)
            self.assertEqual(content[108:].count('filename=doc1.png'), 1)
            self.assertEqual(content[108:].count('filename=doc3.png'), 1)
        finally:
            server.stop()


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
            msg, _msg = server.check_first_message('Mot de passe de connexion', 2)
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
            msg, _msg, = server.check_first_message('Mot de passe de connexion', 2)
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
            msg1, msg2, = server.check_first_message('Mot de passe de connexion', 2)
            self.assertEqual('text/html', msg1.get_content_type())
            self.assertEqual('text/plain', msg2.get_content_type())
            self.assertEqual('base64', msg1.get('Content-Transfer-Encoding', ''))
            message = decode_b64(msg1.get_payload())
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
