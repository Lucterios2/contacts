# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.conf import settings
from django.utils import translation
from django.db import models, migrations

from lucterios.CORE.models import PrintModel
from lucterios.mailing.models import Message
from django.db.models import deletion


def addons_values(apps, schema_editor):
    translation.activate(settings.LANGUAGE_CODE)

    prtmdl = PrintModel.objects.create(
        name="mailing", kind=2, modelname=Message.get_long_name())
    prtmdl.value = """
<model hmargin="10.0" vmargin="10.0" page_width="210.0" page_height="297.0">
<header extent="25.0">
<text height="20.0" width="120.0" top="5.0" left="70.0" padding="1.0" spacing="0.0" border_color="black" border_style="" border_width="0.2" text_align="center" line_height="20" font_family="sans-serif" font_weight="" font_size="20">
{[b]}#OUR_DETAIL.name{[/b]}
</text>
<image height="25.0" width="30.0" top="0.0" left="10.0" padding="1.0" spacing="0.0" border_color="black" border_style="" border_width="0.2">
#OUR_DETAIL.image
</image>
</header>
<bottom extent="10.0">
<text height="10.0" width="190.0" top="00.0" left="0.0" padding="1.0" spacing="0.0" border_color="black" border_style="" border_width="0.2" text_align="center" line_height="8" font_family="sans-serif" font_weight="" font_size="8">
{[i]}#OUR_DETAIL.address #OUR_DETAIL.postal_code #OUR_DETAIL.city - #OUR_DETAIL.tel1 #OUR_DETAIL.email{[br/]}
#OUR_DETAIL.identify_number
{[/i]}
</text>
</bottom>
<body>
<text height="20.0" width="100.0" top="25.0" left="80.0" padding="1.0" spacing="0.0" border_color="black" border_style="" border_width="0.2" text_align="center" line_height="11" font_family="sans-serif" font_weight="" font_size="11">
{[b]}#contact.str{[/b]}{[br/]}
#contact.address{[br/]}
#contact.postal_code #contact.city
</text>
<text height="20.0" width="130.0" top="55.0" left="20.0" padding="1.0" spacing="0.0" border_color="black" border_style="" border_width="0.2">
{[u]}#subject{[/u]}
</text>
<text height="20.0" width="40.0" top="55.0" left="150.0" padding="1.0" spacing="0.0" border_color="black" border_style="" border_width="0.2">
{[i]}#date{[/i]}
</text>
<text height="150.0" width="190.0" top="80.0" left="0.0" padding="1.0" spacing="0.0" border_color="black" border_style="" border_width="0.2">
#body
</text>
</body>
</model>
"""
    prtmdl.save()


class Migration(migrations.Migration):

    dependencies = [
        ('mailing', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Message',
            fields=[
                ('id', models.AutoField(
                    auto_created=True, verbose_name='ID', serialize=False, primary_key=True)),
                ('subject', models.CharField(
                    max_length=50, verbose_name='subject')),
                ('body', models.TextField(default='', verbose_name='body')),
                ('status', models.IntegerField(
                    verbose_name='status', default=0, choices=[(0, 'open'), (1, 'close')])),
                ('recipients', models.TextField(
                    default='', null=False, verbose_name='recipients')),
                ('date', models.DateField(null=True, verbose_name='date')),
                ('contact', models.ForeignKey(on_delete=deletion.SET_NULL,
                                              verbose_name='contact', null=True, to='contacts.AbstractContact')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.RunPython(addons_values),
    ]
