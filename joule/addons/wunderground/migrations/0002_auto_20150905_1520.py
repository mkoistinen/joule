# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('wunderground', '0001_initial'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='weatherdata',
            options={'verbose_name': 'data', 'verbose_name_plural': 'data'},
        ),
    ]
