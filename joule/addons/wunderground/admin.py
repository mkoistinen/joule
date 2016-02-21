# -*- coding: utf-8 -*-

from __future__ import unicode_literals

from django.contrib import admin

from joule.addons.common.admin import LogAdmin

from .models import WeatherData


class WeatherDataAdmin(LogAdmin):

    list_display = ("timestamp",
                    "outside_temp",
                    "outside_humidity",
                    "barometric_pressure")

admin.site.register(WeatherData, WeatherDataAdmin)
