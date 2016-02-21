# -*- coding: utf-8 -*-

from __future__ import unicode_literals
from django.utils.encoding import python_2_unicode_compatible

from datetime import datetime, timedelta
from tzlocal import get_localzone
import pytz

from django.db import models, connection
from django.utils.timezone import now
from django.utils.translation import ugettext_lazy as _


@python_2_unicode_compatible
class EfergyData(models.Model):
    """
    This is the data produced by an Efergy energy monitoring device.
    """
    timestamp = models.DateTimeField(_('timestamp'))
    watts = models.DecimalField(_('watts'), max_digits=12, decimal_places=6)

    class Meta:
        verbose_name = _('log datum')
        verbose_name_plural = _('log data')
        unique_together = [('timestamp', 'watts', ), ]

    def __str__(self):
        return "{watts}W measured at {timestamp}".format(
            watts=self.watts,
            timestamp=self.timestamp.astimezone(get_localzone()))


@python_2_unicode_compatible
class MinuteData(models.Model):
    """
    Efergy data on a per minute basis. This is averaged from the raw log data
    (which is every 10 seconds). Minute is from 0 - 1439 and reflects the number
    of minutes past since midnight.
    """
    timestamp = models.DateTimeField(_('timestamp'), unique=True)
    minute = models.PositiveSmallIntegerField(_('minute'))
    watts = models.DecimalField(_('watts'), max_digits=12, decimal_places=6)

    class Meta:
        verbose_name = _('minute datum')
        verbose_name_plural = _('minute data')

    @classmethod
    def create_from_raw(cls):
        """
        Creates MinuteData from raw EfergyData
        """
        try:
            latest_minute = cls.objects.latest('timestamp')
            start_time = latest_minute.timestamp
            # Why do I have to do this?!?!
            start_time = start_time + timedelta(minutes=1)
            start_time = start_time.astimezone(get_localzone())
        except cls.DoesNotExist:
            start_time = pytz.utc.localize(datetime(2000, 1, 1, 0, 0, 0))

        last_minute = now().replace(second=0, microsecond=0)
        end_time = last_minute.astimezone(get_localzone())

        cursor = connection.cursor()
        # NOTE: This code is MySQL-specific!
        # NOTE: When taking the HOUR() or MINUTE() from a datetime column, it
        # is important to explicitly convert the value to the local timezone
        # first otherwise, the calculations will be for UTC.
        cursor.execute("""
            INSERT INTO efergy_minutedata (
                SELECT
                    NULL,
                    FROM_UNIXTIME(FLOOR(UNIX_TIMESTAMP(`timestamp`)/60)*60) as 'timestamp',
                    HOUR(CONVERT_TZ(`timestamp`, '+00:00', @@global.time_zone)) * 60 + MINUTE(CONVERT_TZ(`timestamp`, '+00:00', @@global.time_zone)) as 'minute',
                    TRUNCATE(AVG(`watts`), 6) as 'watts'
                FROM `efergy_efergydata`
                WHERE `timestamp` >= %s AND `timestamp` < %s
                GROUP BY 2
            ) ON DUPLICATE KEY UPDATE `timestamp`=`timestamp`""",
            (start_time, end_time))

    def __str__(self):
        return "{watts}W measured at {timestamp}".format(
            watts=self.watts, timestamp=self.timestamp)

