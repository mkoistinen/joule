# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import kronos

from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from ...models import EfergyData, MinuteData


def get_minute_coverage(now=None):

    # Let's make sure its up-to-date before we make reports on it...

    MinuteData.create_from_raw()

    now = now or timezone.now()
    now = now.replace(second=0) - timedelta(minutes=1)

    one_day_ago = now - timedelta(days=1)
    one_hour_ago = now - timedelta(hours=1)
    one_week_ago = now - timedelta(days=7)
    one_month_ago = now - timedelta(days=30)

    day_logs = MinuteData.objects.filter(timestamp__gt=one_day_ago).count()
    hour_logs = MinuteData.objects.filter(timestamp__gt=one_hour_ago).count()
    week_logs = MinuteData.objects.filter(timestamp__gt=one_week_ago).count()
    month_logs = MinuteData.objects.filter(timestamp__gt=one_month_ago).count()

    hour_pct = float(hour_logs) / 60.0 * 100
    day_pct = float(day_logs) / 1440.0 * 100
    week_pct = float(week_logs) / (7 * 1440.0) * 100
    month_pct = float(month_logs) / (30 * 1440.0) * 100

    return hour_pct, day_pct, week_pct, month_pct


def get_raw_coverage(now=None):
    now = now or timezone.now()
    one_day_ago = now - timedelta(days=1)
    one_hour_ago = now - timedelta(hours=1)
    one_week_ago = now - timedelta(days=7)
    one_month_ago = now - timedelta(days=30)

    day_logs = EfergyData.objects.filter(timestamp__gt=one_day_ago).count()
    hour_logs = EfergyData.objects.filter(timestamp__gt=one_hour_ago).count()
    week_logs = EfergyData.objects.filter(timestamp__gt=one_week_ago).count()
    month_logs = EfergyData.objects.filter(timestamp__gt=one_month_ago).count()

    hour_pct = float(hour_logs) / 360.0 * 100
    day_pct = float(day_logs) / 8640.0 * 100
    week_pct = float(week_logs) / (7 * 8640.0) * 100
    month_pct = float(month_logs) / (30 * 8640.0) * 100

    return hour_pct, day_pct, week_pct, month_pct


@kronos.register("15 * * * *")
class Command(BaseCommand):

    help = """Reports percentage of data coverage.
    """

    def handle(self, *args, **kwargs):
        now = timezone.now()

        (raw_hour_pct, raw_day_pct, raw_week_pct,
         raw_month_pct) = get_raw_coverage(now)
        print(
            "Raw data coverage    (h,d,w,m): {hour:6.2f}% {day:6.2f}% "
            "{week:6.2f}% {month:6.2f}%".format(
                hour=raw_hour_pct,
                day=raw_day_pct,
                week=raw_week_pct,
                month=raw_month_pct
            ))

        (minute_hour_pct, minute_day_pct, minute_week_pct,
         minute_month_pct) = get_minute_coverage(now)
        print(
            "Minute data coverage (h,d,w,m): {hour:6.2f}% {day:6.2f}% "
            "{week:6.2f}% {month:6.2f}%".format(
                hour=minute_hour_pct,
                day=minute_day_pct,
                week=minute_week_pct,
                month=minute_month_pct
            ))
