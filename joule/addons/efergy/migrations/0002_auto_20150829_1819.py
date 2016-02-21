# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('efergy', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='MinuteData',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('timestamp', models.DateTimeField(unique=True, verbose_name='timestamp')),
                ('minute', models.PositiveSmallIntegerField(verbose_name='minute')),
                ('watts', models.DecimalField(verbose_name='watts', max_digits=12, decimal_places=6)),
            ],
            options={
                'verbose_name': 'minute datum',
                'verbose_name_plural': 'minute data',
            },
        ),
        migrations.AlterModelOptions(
            name='efergydata',
            options={'verbose_name': 'log datum', 'verbose_name_plural': 'log data'},
        ),
    ]
