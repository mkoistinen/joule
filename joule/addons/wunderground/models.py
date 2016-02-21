# -*- coding: utf-8 -*-

from __future__ import unicode_literals
from django.utils.encoding import python_2_unicode_compatible

from tzlocal import get_localzone

from django.db import models
from django.utils.translation import ugettext_lazy as _


@python_2_unicode_compatible
class WeatherData(models.Model):

    timestamp = models.DateTimeField(_('timestamp'), unique=True)
    outside_temp = models.DecimalField(
        max_digits=5, decimal_places=2,
        help_text="Outside temperature in degrees Fahrenheit.")
    outside_humidity = models.DecimalField(
        max_digits=5, decimal_places=2, help_text="Relative humidity (%).")
    barometric_pressure = models.DecimalField(
        max_digits=7, decimal_places=2,
        help_text="Barometric pressure in millibars.")

    class Meta:
        verbose_name = _('data')
        verbose_name_plural = _('data')

    def __str__(self):
        return "Basic weather info @ {0}".format(
            self.timestamp.astimezone(get_localzone()))
