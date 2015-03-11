# -*- coding: utf-8 -*-
# pylint: disable=invalid-name
from __future__ import unicode_literals

from django.db import models, migrations, transaction
from django.utils import six
from os import listdir
from os.path import dirname, join
from django.db.utils import IntegrityError
from django.utils.log import getLogger

def initial_values(apps, schema_editor):
    # pylint: disable=unused-argument
    postalcode = apps.get_model("contacts", "PostalCode")
    migrat_dir = dirname(__file__)
    for pcfile in listdir(migrat_dir):
        if pcfile.endswith(".csv") and pcfile.startswith('postalcode_'):
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
        migrations.RunPython(initial_values),
    ]
