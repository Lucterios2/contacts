# Generated by Django 3.2 on 2021-04-28 14:13

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('mailing', '0009_message_message_type'),
    ]

    operations = [
        migrations.CreateModel(
            name='MessageLine',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('line', models.TextField(default='', verbose_name='line')),
            ],
            options={
                'verbose_name': 'body',
                'verbose_name_plural': 'bodies',
                'default_permissions': [],
            },
        ),
    ]
