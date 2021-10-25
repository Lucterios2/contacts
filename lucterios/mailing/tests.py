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
from email.header import decode_header

from django.contrib.auth.models import AnonymousUser

from lucterios.framework.test import LucteriosTest
from lucterios.framework.filetools import get_user_dir
from lucterios.framework.tools import get_binay
from lucterios.CORE.models import Parameter, LucteriosUser, LucteriosGroup
from lucterios.CORE.views_usergroup import UsersEdit
from lucterios.CORE.views import AskPassword, AskPasswordAct, ParamEdit, ParamSave

from lucterios.contacts.tests_contacts import change_ourdetail, create_jack
from lucterios.contacts.views import CreateAccount
from lucterios.contacts.models import Individual, LegalEntity

from lucterios.mailing.views import Configuration, SendEmailTry, SendSmsTry
from lucterios.mailing.email_functions import will_mail_send, send_email, EmailException
from lucterios.mailing.test_tools import configSMTP, decode_b64, TestReceiver,\
    configSMS, clean_sms_testfile, read_sms


class ConfigurationTest(LucteriosTest):

    def __init__(self, methodName):
        LucteriosTest.__init__(self, methodName)
        self.server = TestReceiver()

    def setUp(self):
        change_ourdetail()
        LucteriosTest.setUp(self)
        rmtree(get_user_dir(), True)
        self.server.start(1025)
        clean_sms_testfile(create_new=False)

    def tearDown(self):
        self.server.stop()
        LucteriosTest.tearDown(self)

    def test_config(self):
        self.factory.xfer = Configuration()
        self.calljson('/lucterios.mailing/configuration', {}, False)
        self.assert_observer('core.custom', 'lucterios.mailing', 'configuration')
        self.assertEqual(len(self.json_context), 0)
        self.assert_count_equal('', 3 + 11 + 3 + 3)  # Nb tab + params email + message + params sms
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
        self.assert_json_equal('LABELFORM', 'mailing-sms-provider', None)

    def test_tryemail_noconfig(self):
        configSMTP('', 25)
        self.assertEqual(0, self.server.count())
        self.factory.xfer = SendEmailTry()
        self.calljson('/lucterios.mailing/sendEmailTry', {}, False)
        self.assert_observer('core.exception', 'lucterios.mailing', 'sendEmailTry')
        self.assert_json_equal('', "message", "Mauvais paramètrage du courriel")
        self.assertEqual(0, self.server.count())

    def create_dkim_file(self):
        try:
            from Crypto.PublicKey import RSA
            dkim_private_file = join(get_user_dir(), "private.pem")
            key = RSA.generate(1024)
            pv_key_string = key.export_key()
            with open(dkim_private_file, "wb") as prv_file:
                prv_file.write(pv_key_string)
        except Exception:
            dkim_private_file = ""
        return dkim_private_file

    def test_tryemail_success(self):
        dkim_private_file = self.create_dkim_file()
        configSMTP('localhost', 1025, dkim_private_file=dkim_private_file)
        self.server.smtp.wrong_email = 'titi@machin.com'
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
            print("-- NO DKIM --")

        msg_text, msg_html = self.server.check_first_message('Essai de courriel', 2)
        self.assertEqual('text/html', msg_html.get_content_type())
        self.assertEqual('text/plain', msg_text.get_content_type())
        self.assertEqual('base64', msg_text.get('Content-Transfer-Encoding', ''))
        self.assertEqual('Courriel envoyé pour vérifier la configuration  \n  \nWoldCompany', decode_b64(msg_text.get_payload())[:63])

        self.factory.xfer = SendEmailTry()
        self.calljson('/lucterios.mailing/sendEmailTry', {'CONFIRME': 'YES', "recipient": 'behoa@worldcompany.com;titi@machin.com'}, False)
        self.assert_observer('core.exception', 'lucterios.mailing', 'sendEmailTry')
        self.assertEqual(2, self.server.count())

    def test_sms_config(self):
        from django.conf import settings
        setattr(settings, "MAILING_TESTSMS", True)

        self.factory.xfer = Configuration()
        self.calljson('/lucterios.mailing/configuration', {}, False)
        self.assert_observer('core.custom', 'lucterios.mailing', 'configuration')
        self.assert_count_equal('', 3 + 11 + 3 + 3)  # Nb tab + params email + message + params sms
        self.assert_json_equal('LABELFORM', 'mailing-sms-provider', None)

        self.factory.xfer = ParamEdit()
        self.calljson('/CORE/paramEdit', {'params': 'mailing-sms-provider'}, False)
        self.assert_observer('core.custom', 'CORE', 'paramEdit')
        self.assert_select_equal('mailing-sms-provider', {'': None, 'TestProvider': 'Test provider', 'MailjetProvider': 'Mailjet SMS'})

        self.factory.xfer = ParamSave()
        self.calljson('/CORE/paramSave', {'params': 'mailing-sms-provider', 'mailing-sms-provider': 'TestProvider'}, False)
        self.assert_observer('core.acknowledge', 'CORE', 'paramSave')

        self.factory.xfer = Configuration()
        self.calljson('/lucterios.mailing/configuration', {}, False)
        self.assert_observer('core.custom', 'lucterios.mailing', 'configuration')
        self.assert_count_equal('', 3 + 11 + 3 + 8)  # Nb tab + params email + message + params sms
        self.assert_json_equal('LABELFORM', 'mailing-sms-provider', 'Test provider')
        self.assert_json_equal('LABELFORM', 'mailing-sms-phone-parse', '^0([67][0-9]{8})$|+33{0}')
        self.assert_json_equal('LABELFORM', 'mailing-sms-option', 'file name = /tmp/sms.txt{[br/]}max = 10')
        self.assert_json_equal('LABELFORM', 'error_sms', "File '/tmp/sms.txt' not found !")

        clean_sms_testfile(create_new=True)

        self.factory.xfer = Configuration()
        self.calljson('/lucterios.mailing/configuration', {}, False)
        self.assert_observer('core.custom', 'lucterios.mailing', 'configuration')
        self.assert_count_equal('', 3 + 11 + 3 + 8)  # Nb tab + params email + message + params sms
        self.assert_json_equal('BUTTON', 'trysms', '')

    def test_trysms(self):
        self.factory.xfer = SendSmsTry()
        self.calljson('/lucterios.mailing/sendSmsTry', {}, False)
        self.assert_observer('core.exception', 'lucterios.mailing', 'sendSmsTry')
        self.assert_json_equal('', "message", "Mauvais paramètrage du SMS")

        configSMS()

        self.factory.xfer = SendSmsTry()
        self.calljson('/lucterios.mailing/sendSmsTry', {}, False)
        self.assert_observer('core.exception', 'lucterios.mailing', 'sendSmsTry')
        self.assert_json_equal('', "message", "Mauvais paramètrage du SMS")

        clean_sms_testfile(create_new=True)

        self.factory.xfer = SendSmsTry()
        self.calljson('/lucterios.mailing/sendSmsTry', {}, False)
        self.assert_observer('core.custom', 'lucterios.mailing', 'sendSmsTry')
        self.assert_json_equal('EDIT', "phone", '0123456789')

        self.factory.xfer = SendSmsTry()
        self.calljson('/lucterios.mailing/sendSmsTry', {'CONFIRME': 'YES', "phone": '01-23-45-67-89'}, False)
        self.assert_observer('core.exception', 'lucterios.mailing', 'sendSmsTry')
        self.assert_json_equal('', "message", "Mauvais numéro de téléphone '01-23-45-67-89' !")

        self.factory.xfer = SendSmsTry()
        self.calljson('/lucterios.mailing/sendSmsTry', {'CONFIRME': 'YES', "phone": '06-23-45-67-89'}, False)
        self.assert_observer('core.dialogbox', 'lucterios.mailing', 'sendSmsTry')
        self.assert_json_equal('', 'text', 'SMS envoyé, veuillez le vérifier.')

        self.factory.xfer = SendSmsTry()
        self.calljson('/lucterios.mailing/sendSmsTry', {'CONFIRME': 'YES', "phone": '07 23.45.6789'}, False)
        self.assert_observer('core.dialogbox', 'lucterios.mailing', 'sendSmsTry')

        self.factory.xfer = SendSmsTry()
        self.calljson('/lucterios.mailing/sendSmsTry', {'CONFIRME': 'YES', "phone": '0623456789'}, False)
        self.assert_observer('core.dialogbox', 'lucterios.mailing', 'sendSmsTry')

        self.assertEqual(read_sms(), ["WoldCompany : +33623456789 => 'SMS envoyé pour vérifier la configuration'\n",
                                      "WoldCompany : +33723456789 => 'SMS envoyé pour vérifier la configuration'\n",
                                      "WoldCompany : +33623456789 => 'SMS envoyé pour vérifier la configuration'\n"])

        self.factory.xfer = SendSmsTry()
        self.calljson('/lucterios.mailing/sendSmsTry', {'CONFIRME': 'YES', "phone": '0623456789'}, False)
        self.assert_observer('core.exception', 'lucterios.mailing', 'sendSmsTry')
        self.assert_json_equal('', "message", "File '/tmp/sms.txt' too long !")

    def test_send_no_config(self):
        configSMTP('', 25)
        self.assertEqual(0, self.server.count())
        self.assertEqual(False, will_mail_send())
        try:
            send_email('toto@machin.com', 'send without config', 'boom!!!')
            self.assertTrue(False)
        except EmailException as error:
            self.assertEqual(str(error), 'Courriel non configuré !')
        self.assertEqual(0, self.server.count())

    def test_send_bad_config(self):
        configSMTP('localhost', 1125)
        self.assertEqual(0, self.server.count())
        self.assertEqual(True, will_mail_send())
        try:
            send_email('toto@machin.com', 'send without config', 'boom!!!')
            self.assertTrue(False)
        except EmailException as error:
            self.assertEqual(str(error)[:11], '[Errno 111]')
        self.assertEqual(0, self.server.count())

    def test_send_ok(self):
        configSMTP('localhost', 1025)
        self.assertEqual(0, self.server.count())
        self.assertEqual(True, will_mail_send())
        ret = send_email('toto@machin.com', 'send correct config', 'Yessss!!!')
        self.assertEqual({}, ret)
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
        ret = send_email('toto@machin.com', 'send correct config', 'Yessss!!!', withcopy=True)
        self.assertEqual({}, ret)
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
        ret = send_email(['toto@machin.com', 'titi@machin.com'], 'send correct config', 'Yessss!!!')
        self.assertEqual({}, ret)
        self.assertEqual(1, self.server.count())
        self.assertEqual('mr-sylvestre@worldcompany.com', self.server.get(0)[1])
        self.assertEqual(['toto@machin.com', 'titi@machin.com'], self.server.get(0)[2])
        msg, = self.server.check_first_message('send correct config', 1, {'To': 'toto@machin.com, titi@machin.com', 'Cc': ''})
        self.assertEqual('text/plain', msg.get_content_type())
        self.assertEqual('base64', msg.get('Content-Transfer-Encoding', ''))
        self.assertEqual('Yessss!!!', decode_b64(msg.get_payload()))
        self.assertEqual(None, self.server.smtp.auth_params)

    def test_send_multi_dest_with_refuse(self):
        configSMTP('localhost', 1025)
        self.server.smtp.wrong_email = 'titi@machin.com'
        self.assertEqual(0, self.server.count())
        self.assertEqual(True, will_mail_send())
        ret = send_email(['toto@machin.com', 'titi@machin.com'], 'send with refuse', 'Yessss!!!')
        self.assertEqual(['titi@machin.com'], list(ret.keys()))
        self.assertEqual(1, self.server.count())
        self.assertEqual('mr-sylvestre@worldcompany.com', self.server.get(0)[1])
        self.assertEqual(['toto@machin.com'], self.server.get(0)[2])
        msg, = self.server.check_first_message('send with refuse', 1, {'To': 'toto@machin.com, titi@machin.com', 'Cc': ''})
        self.assertEqual('text/plain', msg.get_content_type())
        self.assertEqual('base64', msg.get('Content-Transfer-Encoding', ''))
        self.assertEqual('Yessss!!!', decode_b64(msg.get_payload()))
        self.assertEqual(None, self.server.smtp.auth_params)

    def test_send_multi_email(self):
        configSMTP('localhost', 1025)
        self.assertEqual(0, self.server.count())
        self.assertEqual(True, will_mail_send())
        ret = send_email(['toto@machin.com;titi@machin.com,tutu@machin.com'], 'send correct config', 'Yessss!!!')
        self.assertEqual({}, ret)
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
        ret = send_email('toto@machin.com', 'send correct config', 'Yessss!!!', cclist=['titi@machin.com', 'tutu@machin.com'])
        self.assertEqual({}, ret)
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
        ret = send_email('toto@machin.com', 'send correct config', 'Yessss!!!', bcclist=['titi@machin.com', 'tutu@machin.com'])
        self.assertEqual({}, ret)
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
        ret = send_email(['toto@machin.com', 'titi@machin.com', 'tyty@machin.com'], 'send correct config', 'Yessss!!!',
                         cclist=['titi@machin.com', 'tutu@machin.com', 'tata@machin.com'], bcclist=['toto@machin.com', 'tutu@machin.com', 'tete@machin.com'])
        self.assertEqual({}, ret)
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
        html_content = """<html>
<body>
    <h1>Yessss!!!</h1>
    En here, there are a nice <a href='https://truc-muche-machin.zb/aaaa_aaa/bbbb-bbbb/cccc.cccc/dddd%20dddd/bidule.pdf'>link</a>.
</body>
</html>"""
        ret = send_email('toto@machin.com', 'send html', html_content)
        self.assertEqual({}, ret)
        self.assertEqual(1, self.server.count())
        self.assertEqual('mr-sylvestre@worldcompany.com', self.server.get(0)[1])
        self.assertEqual(['toto@machin.com'], self.server.get(0)[2])
        msg2, msg1, = self.server.check_first_message('send html', 2)
        self.assertEqual('text/html', msg1.get_content_type())
        self.assertEqual('base64', msg1.get('Content-Transfer-Encoding', ''))
        self.assertEqual(html_content, decode_b64(msg1.get_payload()))
        self.assertEqual('text/plain', msg2.get_content_type())
        self.assertEqual('base64', msg2.get('Content-Transfer-Encoding', ''))
        self.assertEqual("""# Yessss!!!

En here, there are a nice [link](https://truc-muche-machin.zb/aaaa_aaa/bbbb-bbbb/cccc.cccc/dddd%20dddd/bidule.pdf).""", decode_b64(msg2.get_payload()).strip())

    def test_send_with_auth(self):
        self.server.smtp.with_authentificate = True
        configSMTP('localhost', 1025, 0, 'toto', 'abc123')
        self.assertEqual(0, self.server.count())
        self.assertEqual(True, will_mail_send())
        ret = send_email('toto@machin.com', 'send with auth', 'OK!')
        self.assertEqual({}, ret)
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
        except EmailException as error:
            self.assertEqual(str(error), 'STARTTLS extension not supported by server.')
        self.assertEqual(0, self.server.count())

    def test_send_with_ssl(self):
        configSMTP('localhost', 1025, 2)
        self.assertEqual(0, self.server.count())
        self.assertEqual(True, will_mail_send())
        try:
            send_email('toto@machin.com', 'send with ssl', 'not success!')
            self.assertTrue(False)
        except EmailException as error:
            self.assertTrue(('unknown protocol' in str(error)) or ('SSL: WRONG_VERSION_NUMBER' in str(error)), str(error))
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
        self.assert_count_equal('', 17)

    def test_user_withconfig(self):
        configSMTP('localhost', 1025)
        self.factory.xfer = UsersEdit()
        self.calljson('/CORE/usersEdit', {}, False)
        self.assert_observer('core.custom', 'CORE', 'usersEdit')
        self.assert_count_equal('', 18)
        self.assert_attrib_equal("password_generate", "description", "Générer un nouveau mot de passe?")

    def test_user_change_password(self):
        configSMTP('localhost', 1025)
        self.assertEqual(0, self.server.count())
        self.factory.xfer = UsersEdit()
        self.calljson('/CORE/usersEdit', {'SAVE': 'YES', 'user_actif': '1',
                                          "password_generate": 'o', "email": 'admin@super.com'}, False)
        self.assert_observer('core.acknowledge', 'CORE', 'usersEdit')
        self.assertEqual(1, self.server.count())
        _msg, msg = self.server.check_first_message('Mot de passe de connexion', 2)
        self.assertEqual('text/html', msg.get_content_type())
        self.assertEqual('base64', msg.get('Content-Transfer-Encoding', ''))
        content_msg = decode_b64(msg.get_payload())
        self.assertEqual('<html>Bienvenue<br/><br/>Confirmation de connexion à votre application :'
                         '<br/> - Alias : admin<br/> - Mot de passe : ', content_msg[:116])
        password = content_msg[116:].split('<br/>')[0]
        user = LucteriosUser.objects.get(id=1)
        self.assertTrue(user.check_password(password), content_msg)


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
            _msg, msg = server.check_first_message('Mot de passe de connexion', 2)
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
        new_groupe = LucteriosGroup.objects.create(name='new_groupe')
        param = Parameter.objects.get(name='contacts-defaultgroup')
        param.value = '%d' % new_groupe.id
        param.save()
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
            self.assert_action_equal('POST', self.response_json['action'], ('', None, 'lucterios.contacts', 'createAccount', 1, 1, 1, {
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
            _msg, msg, = server.check_first_message('Mot de passe de connexion', 2)
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
        self.assertEqual([new_groupe], list(user.groups.all()))
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
            msg2, msg1, = server.check_first_message('Mot de passe de connexion', 2)
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
        self.assertEqual([], list(user.groups.all()))
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
