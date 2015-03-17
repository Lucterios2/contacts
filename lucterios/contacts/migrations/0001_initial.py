# -*- coding: utf-8 -*-
# pylint: disable=invalid-name
from __future__ import unicode_literals

from django.db import models, migrations, transaction
from django.db.utils import IntegrityError
from django.conf import settings
from django.utils.log import getLogger
from django.utils import six

from os import listdir
from os.path import dirname, join
import sys

def initial_values(apps, schema_editor):
    # pylint: disable=unused-argument
    legalentity = apps.get_model("contacts", "LegalEntity")
    current_entity = legalentity.objects.create(id=1, name="---", address='---', \
                            postal_code='00000', city='---', country='---')
    current_entity.save()

def initial_postalcodes(apps, schema_editor):
    # pylint: disable=unused-argument
    import codecs
    pcfilename_prefix = 'postalcode_'
    if (len(sys.argv) >= 2) and (sys.argv[1] == 'test'):
        pcfilename_prefix = 'postalcode_frDOMTOM'
    postalcode = apps.get_model("contacts", "PostalCode")
    migrat_dir = dirname(__file__)
    for pcfile in listdir(migrat_dir):
        if pcfile.endswith(".csv") and pcfile.startswith(pcfilename_prefix):
            with codecs.open(join(migrat_dir, pcfile), 'r', 'utf-8') as flpc:
                for line in flpc.readlines():
                    try:
                        postal_code, city, country = six.text_type(line).split(';')[:3]
                        with transaction.atomic():
                            newpc = postalcode.objects.create()
                            newpc.postal_code = six.text_type(postal_code).strip()
                            newpc.city = six.text_type(city).strip()
                            newpc.country = six.text_type(country).strip()
                            newpc.save()
                    except IntegrityError:
                        getLogger(__name__).warning(six.text_type(" --- IntegrityError:") + six.text_type(line))

class Migration(migrations.Migration):

    dependencies = [
        (six.text_type("auth"), six.text_type("0001_initial")),
        (six.text_type("CORE"), six.text_type("0001_initial")),
    ]

    operations = [
        migrations.CreateModel(
            name='PostalCode',
            fields=[
                ('id', models.AutoField(serialize=False, auto_created=True, verbose_name='ID', primary_key=True)),
                ('postal_code', models.CharField(max_length=10, blank=False, verbose_name='postal code')),
                ('city', models.CharField(max_length=100, blank=False, verbose_name='city')),
                ('country', models.CharField(max_length=100, blank=False, verbose_name='country')),
            ],
            options={
                'verbose_name_plural': 'postal codes',
                'verbose_name': 'postal code',
                'default_permissions': ['add', 'change'],
                'ordering': ['postal_code', 'city'],
                'unique_together': (('postal_code', 'city', 'country'),)
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Function',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, verbose_name='ID', serialize=False)),
                ('name', models.CharField(unique=True, max_length=50, verbose_name='name')),
            ],
            options={
                'default_permissions': [],
                'verbose_name': 'Individual function',
                'verbose_name_plural': 'Individual functions'
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='StructureType',
            fields=[
                ('id', models.AutoField(primary_key=True, verbose_name='ID', serialize=False, auto_created=True)),
                ('name', models.CharField(unique=True, max_length=50, verbose_name='name')),
            ],
            options={
                'default_permissions': [],
                'verbose_name': 'structure type',
                'verbose_name_plural': 'structure types'
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='AbstractContact',
            fields=[
                ('id', models.AutoField(serialize=False, auto_created=True, primary_key=True, verbose_name='ID')),
                ('address', models.TextField(verbose_name='address', blank=False)),
                ('postal_code', models.CharField(max_length=10, verbose_name='postal code', blank=False)),
                ('city', models.CharField(max_length=100, verbose_name='city', blank=False)),
                ('country', models.CharField(max_length=100, verbose_name='country', blank=False)),
                ('tel1', models.CharField(max_length=15, blank=True, verbose_name='phone #1')),
                ('tel2', models.CharField(max_length=15, blank=True, verbose_name='phone #2')),
                ('email', models.EmailField(max_length=75, blank=True, verbose_name='email')),
                ('comment', models.TextField(blank=True, verbose_name='comment')),
            ],
            options={
                'default_permissions': [],
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='LegalEntity',
            fields=[
                ('abstractcontact_ptr', models.OneToOneField(auto_created=True, to='contacts.AbstractContact', serialize=False, parent_link=True, primary_key=True)),
                ('name', models.CharField(max_length=100, verbose_name='name', blank=False)),
                ('identify_number', models.CharField(max_length=100, blank=True, verbose_name='legal number')),
                ('structure_type', models.ForeignKey(null=True, to='contacts.StructureType')),
            ],
            options={
                'verbose_name_plural': 'legal entities',
                'verbose_name': 'legal entity',
            },
            bases=('contacts.abstractcontact',),
        ),
        migrations.CreateModel(
            name='Individual',
            fields=[
                ('abstractcontact_ptr', models.OneToOneField(auto_created=True, to='contacts.AbstractContact', serialize=False, parent_link=True, primary_key=True)),
                ('firstname', models.CharField(max_length=50, verbose_name='firstname')),
                ('lastname', models.CharField(max_length=50, verbose_name='lastname')),
                ('genre', models.IntegerField(default=1, choices=[(1, 'Man'), (2, 'Woman')], blank=False)),
                ('user', models.ForeignKey(null=True, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name_plural': 'individuals',
                'verbose_name': 'individual',
            },
            bases=('contacts.abstractcontact',),
        ),
        migrations.RunPython(initial_postalcodes),
        migrations.RunPython(initial_values),
    ]
