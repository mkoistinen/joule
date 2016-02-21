# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='EfergyData',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('timestamp', models.DateTimeField(verbose_name='timestamp')),
                ('watts', models.DecimalField(verbose_name='watts', max_digits=12, decimal_places=6)),
            ],
            options={
                'verbose_name': 'data',
                'verbose_name_plural': 'data',
            },
        ),
        migrations.AlterUniqueTogether(
            name='efergydata',
            unique_together=set([('timestamp', 'watts')]),
        ),
    ]
