# -*- coding: utf-8 -*-
# Generated by Django 1.9.3 on 2016-09-24 21:22
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('contacts', '0003_createaccount'),
    ]

    operations = [
        migrations.AlterField(
            model_name='abstractcontact',
            name='tel1',
            field=models.CharField(blank=True, max_length=20, verbose_name='tel1'),
        ),
        migrations.AlterField(
            model_name='abstractcontact',
            name='tel2',
            field=models.CharField(blank=True, max_length=20, verbose_name='tel2'),
        ),
        migrations.AlterField(
            model_name='customfield',
            name='name',
            field=models.CharField(max_length=200, verbose_name='name'),
        ),
        migrations.AlterField(
            model_name='individual',
            name='firstname',
            field=models.CharField(max_length=100, verbose_name='firstname'),
        ),
        migrations.AlterField(
            model_name='individual',
            name='lastname',
            field=models.CharField(max_length=100, verbose_name='lastname'),
        ),
        migrations.AlterField(
            model_name='legalentity',
            name='identify_number',
            field=models.TextField(blank=True, verbose_name='identify number'),
        ),
    ]