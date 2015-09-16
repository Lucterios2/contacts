# -*- coding: utf-8 -*-
# pylint: disable=invalid-name
'''
Initial django functions

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

from django.conf import settings
from django.utils import six, translation
from django.utils.translation import ugettext_lazy as _
from django.db import migrations

from lucterios.CORE.models import Parameter


def initial_values(apps, schema_editor):
    translation.activate(settings.LANGUAGE_CODE)

    param = Parameter.objects.create(name='mailing-smtpserver', typeparam=0)
    param.title = _("mailing-smtpserver")
    param.args = "{'Multi': False}"
    param.value = ''
    param.save()

    param = Parameter.objects.create(name='mailing-smtpport', typeparam=1)
    param.title = _("mailing-smtpport")
    param.args = "{'Min': 0, 'Max': 99999}"
    param.value = '25'
    param.save()

    param = Parameter.objects.create(name='mailing-smtpsecurity', typeparam=4)
    param.title = _("mailing-smtpsecurity")
    param.param_titles = (_("mailing-smtpsecurity.0"),
                          _("mailing-smtpsecurity.1"), _("mailing-smtpsecurity.2"))
    param.args = "{'Enum':3}"
    param.value = '0'
    param.save()

    param = Parameter.objects.create(name='mailing-smtpuser', typeparam=0)
    param.title = _("mailing-smtpuser")
    param.args = "{'Multi': False}"
    param.value = ''
    param.save()

    param = Parameter.objects.create(name='mailing-smtppass', typeparam=5)
    param.title = _("mailing-smtppass")
    param.args = "{'Multi': False}"
    param.value = ''
    param.save()

    param = Parameter.objects.create(
        name='mailing-msg-connection', typeparam=0)
    param.title = _("mailing-msg-connection")
    param.args = "{'Multi': True}"
    param.value = _('''Connection confirmation to your application:
User:%(username)s
Password:%(password)s
''')
    param.save()


class Migration(migrations.Migration):

    dependencies = [
        (six.text_type("CORE"), six.text_type("0001_initial")),
        (six.text_type("contacts"), six.text_type("0001_initial")),
    ]

    operations = [
        migrations.RunPython(initial_values),
    ]
