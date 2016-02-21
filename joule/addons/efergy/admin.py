# -*- coding: utf-8 -*-

from django.contrib import admin

from .models import EfergyData
from joule.addons.common.admin import LogAdmin


class EfergyDataAdmin(LogAdmin):
    list_display = ('timestamp', 'watts')

admin.site.register(EfergyData, EfergyDataAdmin)
