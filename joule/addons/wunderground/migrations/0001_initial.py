# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='WeatherData',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('timestamp', models.DateTimeField(unique=True, verbose_name='timestamp')),
                ('outside_temp', models.DecimalField(help_text='Outside temperature in degrees Fahrenheit.', max_digits=5, decimal_places=2)),
                ('outside_humidity', models.DecimalField(help_text='Relative humidity (%).', max_digits=5, decimal_places=2)),
                ('barometric_pressure', models.DecimalField(help_text='Barometric pressure in millibars.', max_digits=7, decimal_places=2)),
            ],
        ),
    ]
