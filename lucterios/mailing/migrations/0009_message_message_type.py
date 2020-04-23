# Generated by Django 2.2.8 on 2020-04-23 10:01

from django.db import migrations
import django_fsm


class Migration(migrations.Migration):

    dependencies = [
        ('mailing', '0008_documentcontainer'),
    ]

    operations = [
        migrations.AddField(
            model_name='message',
            name='message_type',
            field=django_fsm.FSMIntegerField(choices=[(0, 'email'), (1, 'sms')], default=0, verbose_name='type'),
        ),
    ]
