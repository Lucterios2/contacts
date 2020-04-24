# -*- coding: utf-8 -*-
'''
lucterios.contacts package

@author: Laurent GAY
@organization: sd-libre.fr
@contact: info@sd-libre.fr
@copyright: 2020 sd-libre.fr
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
from os.path import isfile
from re import compile

from django.utils.translation import ugettext_lazy as _

from lucterios.framework.error import LucteriosException, IMPORTANT


class SMSException(LucteriosException):

    def __init__(self, msg):
        LucteriosException.__init__(self, IMPORTANT, msg)


class AbstractProvider(object):

    title = ''
    default_options = {}

    def __init__(self, phone_parse, sender, options):
        self.sender = sender
        self.set_options(options)
        self.phone_check = compile(phone_parse[0])
        self.phone_replace = phone_parse[1] if len(phone_parse) > 0 else ""

    def set_options(self, options):
        self.options = {opt_line.split('=')[0].strip(): opt_line.split('=')[1].strip() for opt_line in options.split('{[br/]}') if opt_line.count('=') == 1}
        for opt_key, opt_val in self.default_options.items():
            if opt_key not in self.options:
                self.options[opt_key] = opt_val

    @property
    def is_active(self):
        return False

    @classmethod
    def simple_phone(cls, phone):
        return "".join([digit for digit in phone if digit in ('0', '1', '2', '3', '4', '5', '6', '7', '8', '9')])

    def convert_sms_phone(self, phone):
        new_phone = None
        regex_phone = self.phone_check.match(self.simple_phone(phone))
        if regex_phone:
            new_phone = self.phone_replace.format(*regex_phone.groups())
        return new_phone

    def has_valid_phone(self, contact, fields):
        valid = False
        for field_name in fields:
            try:
                valid = valid or (self.convert_sms_phone(getattr(contact, field_name, '')) is not None)
            except ValueError:
                pass
        return valid

    @property
    def options_text(self):
        return "{[br/]}".join(["%s = %s" % (opt_key, opt_val) for opt_key, opt_val in self.options.items() if opt_key in self.default_options])

    def send_sms(self, phone, text):
        new_phone = self.convert_sms_phone(phone)
        if new_phone is None:
            raise SMSException(_("Bad phone number '%s' !") % phone)
        else:
            self.send_sms_ex(new_phone, text)

    def send_sms_ex(self, phone, text):
        return

    @classmethod
    def get_provider_list(cls):
        return [('', None)] + [(sub_provider.__name__, sub_provider.title) for sub_provider in cls.__subclasses__()]

    @classmethod
    def get_current_instance(cls):
        from lucterios.CORE.parameters import Params
        from lucterios.contacts.models import LegalEntity
        provider = None
        phone_parse = Params.getvalue('mailing-sms-phone-parse').strip()
        provider_name = Params.getvalue('mailing-sms-provider').strip()
        if provider_name != '':
            for sub_provider in cls.__subclasses__():
                if provider_name == sub_provider.__name__:
                    provider = sub_provider(phone_parse.split('|'), LegalEntity.objects.get(id=1).name, Params.getvalue('mailing-sms-option'))
        return provider

    @classmethod
    def is_current_active(cls):
        provider = cls.get_current_instance()
        return (provider is not None) and provider.is_active


class TestProvider(AbstractProvider):

    title = 'Test provider'
    default_options = {'file name': '/tmp/sms.txt', 'max': 10}

    def set_options(self, options):
        AbstractProvider.set_options(self, options)
        self.options['max'] = int(self.options['max'])

    @property
    def is_active(self):
        return isfile(self.options['file name'])

    def send_sms_ex(self, phone, text):
        sms_file_name = self.options['file name']
        if not isfile(sms_file_name):
            raise SMSException("File '%s' not found !" % sms_file_name)
        with open(sms_file_name, 'r') as sms_file:
            nb_line = len(sms_file.readlines())
        if nb_line >= self.options['max']:
            raise SMSException("File '%s' too long !" % sms_file_name)
        with open(sms_file_name, 'a') as sms_file:
            sms_file.write("%s : %s => '%s'\n" % (self.sender, phone, text.replace('\n', '|')))
        return
