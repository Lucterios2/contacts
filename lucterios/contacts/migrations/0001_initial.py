# -*- coding: utf-8 -*-
# pylint: disable=invalid-name
from __future__ import unicode_literals

from django.db import models, migrations, transaction
from django.utils import six
from os import listdir
from os.path import dirname, join
from django.db.utils import IntegrityError
from django.utils.log import getLogger
import sys
from django.conf import settings

def initial_values(apps, schema_editor):
    # pylint: disable=unused-argument
    legalentity = apps.get_model("contacts", "LegalEntity")
    current_entity = legalentity.objects.create(id=1, name="---", address='---', \
                            postal_code='00000', city='---')
    current_entity.save()

def initial_postalcodes(apps, schema_editor):
    # pylint: disable=unused-argument
    pcfilename_prefix = 'postalcode_'
    if (len(sys.argv) >= 2) and (sys.argv[1] == 'test'):
        pcfilename_prefix = 'postalcode_frDOMTOM'
    postalcode = apps.get_model("contacts", "PostalCode")
    migrat_dir = dirname(__file__)
    for pcfile in listdir(migrat_dir):
        if pcfile.endswith(".csv") and pcfile.startswith(pcfilename_prefix):
            with open(join(migrat_dir, pcfile)) as flpc:
                for line in flpc.readlines():
                    try:
                        postal_code, city, country = six.text_type(line).split(';')[:3]
                        with transaction.atomic():
                            newpc = postalcode.objects.create()
                            newpc.postal_code = six.text_type(postal_code).strip()
                            newpc.city = six.text_type(city).strip()
                            newpc.country = six.text_type(country).strip()
                            newpc.save()
                    except ValueError:
                        getLogger(__name__).warning(six.text_type(" --- ValueError"))
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
                'verbose_name_plural': 'structure types',
                'verbose_name': 'structure type',
                'default_permissions': [],
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='AbstractContact',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('address', models.TextField(verbose_name='address')),
                ('postal_code', models.CharField(max_length=10, verbose_name='postal code')),
                ('city', models.CharField(max_length=100, verbose_name='city')),
                ('country', models.CharField(max_length=100, verbose_name='country')),
                ('tel1', models.CharField(max_length=15, verbose_name='tel1')),
                ('tel2', models.CharField(max_length=15, verbose_name='tel1')),
                ('email', models.EmailField(max_length=75, verbose_name='email')),
                ('comment', models.TextField(verbose_name='comment')),
            ],
            options={
                'default_permissions': [],
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Individual',
            fields=[
                ('abstractcontact_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='contacts.AbstractContact')),
                ('genre', models.IntegerField(choices=[(1, 'Man'), (2, 'Woman')], default=1)),
                ('lastname', models.CharField(max_length=50, verbose_name='lastname')),
                ('firstname', models.CharField(max_length=50, verbose_name='firstname')),
                ('user', models.ForeignKey(to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'individual',
                'verbose_name_plural': 'individuals',
            },
            bases=('contacts.abstractcontact',),
        ),
        migrations.CreateModel(
            name='LegalEntity',
            fields=[
                ('abstractcontact_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='contacts.AbstractContact')),
                ('name', models.CharField(max_length=100, verbose_name='name')),
                ('identify_number', models.CharField(max_length=100, verbose_name='identify number')),
                ('structure_type', models.ForeignKey(to='contacts.StructureType', null=True)),
            ],
            options={
                'verbose_name': 'legal entity',
                'verbose_name_plural': 'legal entities',
            },
            bases=('contacts.abstractcontact',),
        ),
        migrations.RunPython(initial_postalcodes),
        migrations.RunPython(initial_values),
    ]
