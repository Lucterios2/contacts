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
from base64 import b64decode
from os.path import isfile
from os import remove
from subprocess import Popen, PIPE
from threading import Thread
from time import sleep
import logging
import email
import os
import sys

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


class SMTPListen(object):

    def __init__(self, port=25, with_authentificate=False, auth_params=None, wrong_email=None):
        self.emails = []
        self.with_authentificate = with_authentificate
        self.auth_params = auth_params
        self.wrong_email = wrong_email
        self.seen_greeting = None
        self.port = port
        self._current_content = None
        self.smpt_process = None
        self.err_message = b''
        self.thread_list = []

    def _new_email(self, line):
        self._current_content = []
        # self._add_line(line)

    def _add_line(self, line):
        if self._current_content is not None:
            logging.getLogger("lucterios.mailing.test").debug('[email] NEW LINE - PORT=%d - %s', self.port, line)
            self._current_content.append(line)

    def _end_email(self, line):
        # self._add_line(line)
        peer, mailfrom, rcpttos, rcpcc = None, None, None, None
        for line in self._current_content:
            if line.startswith(b'X-Peer:'):
                peer = line[7:].decode().strip()
            if line.startswith(b'From:'):
                mailfrom = line[5:].decode().strip()
                if '<' in mailfrom:
                    mailfrom = mailfrom[mailfrom.index('<') + 1:]
                if '>' in mailfrom:
                    mailfrom = mailfrom[:mailfrom.index('>')]
            if line.startswith(b'To:'):
                rcpttos = [email.strip() for email in line[3:].decode().strip().replace(',', ';').split(';')]
            if line.startswith(b'Cc:'):
                rcpcc = [email.strip() for email in line[3:].decode().strip().replace(',', ';').split(';')]
            if peer and mailfrom and rcpttos and rcpcc:
                break
        if rcpcc is None:
            rcpcc = []
        logging.getLogger("lucterios.mailing.test").info('[email] NEW EMAIL - PORT=%d - %s - %s - %s', self.port, peer, mailfrom, rcpttos)
        self.emails.append((peer, mailfrom, rcpttos + rcpcc, b''.join(self._current_content)))
        self._current_content = None

    def start(self):
        logging.getLogger("lucterios.mailing.test").info('[email] STARTING - PORT=%d', self.port)
        self.smpt_process = Popen("%s -m aiosmtpd -c aiosmtpd.handlers.Debugging -l 127.0.0.1:%d -n" % (sys.executable, self.port),
                                  stdout=PIPE, stderr=PIPE, shell=True)
        self.thread_list.clear()
        self.thread_list.append(Thread(target=self.analyse, daemon=True))
        self.thread_list.append(Thread(target=self.mngerror, daemon=True))
        for thd in self.thread_list:
            thd.start()
        sleep(0.2)
        logging.getLogger("lucterios.mailing.test").debug('[email] STARTED - PORT=%d - %s - %s', self.port, self.err_message, self.smpt_process.poll())

    def mngerror(self):
        with self.smpt_process.stderr:
            for line in iter(self.smpt_process.stderr.readline, b''):
                self.err_message += line
                if self.smpt_process.poll():
                    break

    def analyse(self):
        logging.getLogger("lucterios.mailing.test").debug('[email] ANALYSING - PORT=%d - %s - %s', self.port, self.err_message, self.smpt_process.poll())
        try:
            with self.smpt_process.stdout:
                for line in iter(self.smpt_process.stdout.readline, b''):
                    if self.smpt_process.poll():
                        break
                    if line == b'':
                        print('[email] blank line')
                        continue
                    if b'MESSAGE FOLLOWS' in line:
                        self._new_email(line)
                    elif b'END MESSAGE' in line:
                        self._end_email(line)
                    else:
                        self._add_line(line)
        except Exception:
            logging.getLogger("lucterios.mailing.test").exception('[email] ERROR ANALYSE')
        finally:
            logging.getLogger("lucterios.mailing.test").debug('[email] ANALYSED - PORT=%d - %s\n', self.port, self.err_message.decode())

    def stop(self):
        if self.smpt_process is None:
            logging.getLogger("lucterios.mailing.test").debug('[email] NO STOP - PORT=%d', self.port)
            return
        try:
            logging.getLogger("lucterios.mailing.test").info('[email] STOPING - PORT=%d - %s', self.port, self.smpt_process.pid)
            os.system('pkill -TERM -P {pid}'.format(pid=self.smpt_process.pid))
            self.smpt_process.terminate()
            for thd in self.thread_list:
                thd.join()
        except Exception:
            logging.getLogger("lucterios.mailing.test").exception('[email] ERROR STOP')
        finally:
            self.thread_list.clear()
            self.smpt_process = None
            logging.getLogger("lucterios.mailing.test").debug('[email] STOPED - PORT=%d - %s', self.port, self.err_message.decode())


class TestReceiver(TestCase):

    def __init__(self):
        TestCase.__init__(self, methodName='stop')
        self.smtp = SMTPListen()

    def start(self, port):
        self.smtp = SMTPListen()
        self.smtp.port = port
        self.smtp.start()
        logging.getLogger("lucterios.mailing.test").debug('[email] start reseiver')

    def stop(self):
        self.smtp.stop()

    def count(self):
        sleep(1.0)
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
        def decode_mime_words(text):
            return ''.join(word.decode(encoding or 'utf8') if isinstance(word, bytes) else word for word, encoding in email.header.decode_header(text))
        special_value = {
            "peer": str(self.get(index)[0]),
            "mailfrom": str(self.get(index)[1]),
            "rcpttos": ";".join(self.get(index)[2])
        }
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
                if key in special_value:
                    self.assertEqual(val, special_value[key])
                else:
                    self.assertEqual(val, decode_mime_words(msg.get(key, '')), msg.get(key, ''))
        return self.convert_message(msg.get_payload())

    def check_first_message(self, subject, nb_multi, params=None):
        msg_result = self.get_msg_index(0, subject, params)
        self.assertEqual(nb_multi, len(msg_result))
        return msg_result
