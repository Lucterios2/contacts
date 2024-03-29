# Generated by Django 3.2.16 on 2022-10-26 15:19

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('contacts', '0006_alter_customfield_args'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='customfield',
            options={'default_permissions': [], 'ordering': ['order_key'], 'verbose_name': 'custom field', 'verbose_name_plural': 'custom fields'},
        ),
        migrations.AddField(
            model_name='customfield',
            name='order_key',
            field=models.IntegerField(default=None, null=True, verbose_name='order key'),
        ),
    ]
