# Generated by Django 2.0.6 on 2018-07-03 19:29

from django.db import migrations, models
import django_fsm


class Migration(migrations.Migration):

    dependencies = [
        ('documents', '0002_length_name'),
        ('mailing', '0003_transition'),
    ]

    operations = [
        migrations.AddField(
            model_name='message',
            name='documents',
            field=models.ManyToManyField(blank=True, to='documents.Document', verbose_name='documents'),
        ),
        migrations.AddField(
            model_name='message',
            name='email_sent',
            field=models.TextField(default='', verbose_name='email sent'),
        ),
        migrations.AddField(
            model_name='message',
            name='email_to_send',
            field=models.TextField(default='', verbose_name='email to send'),
        ),
        migrations.AlterField(
            model_name='message',
            name='status',
            field=django_fsm.FSMIntegerField(choices=[(0, 'open'), (1, 'close'), (2, 'sending')], default=0, verbose_name='status'),
        ),
    ]
