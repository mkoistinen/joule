# -*- coding: utf-8 -*-

from __future__ import unicode_literals

from django.contrib import admin


class LogAdmin(admin.ModelAdmin):
    """
    A read-only ModelAdmin suitable for log models.
    """
    def __init__(self, model, admin_site):
        super(LogAdmin, self).__init__(model, admin_site)
        self.readonly_fields = [
            field.name for field in filter(
                lambda f: not f.auto_created, model._meta.fields)]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        if obj is None:
            return True
        else:
            return False
