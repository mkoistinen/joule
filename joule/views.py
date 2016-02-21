# -*- coding: utf-8 -*-

from __future__ import unicode_literals, division

import pytz

from calendar import monthrange
from datetime import datetime, timedelta
from decimal import Decimal
from functools import partial
from tzlocal import get_localzone

from django.db.models import Max, Min, Sum
from django.conf import settings
from django.core.cache import cache
from django.core.urlresolvers import reverse
from django.db import connection
from django.shortcuts import redirect
from django.utils import timezone
from django.views.generic import TemplateView

from .piedmont import (
    is_designated_holiday,
    is_summer,
    piedmont_bill,
    piedmont_tariff,
)

from addons.efergy.models import MinuteData
from addons.efergy.management.commands.data_coverage import get_minute_coverage
from addons.wunderground.models import WeatherData
from .utils import safe_cache_key
from .tariffs import is_weekend


WEEKEND = "weekend"
SUMMER = "summer"
WINTER = "winter"

ZERO = Decimal(0.0)


def get_day_data(day, use_cache=True):
    """Given a single day, return summary data, but in a cached manner."""
    cache_key = safe_cache_key("joule:views:get_day_cache:" + str(day.date()))
    data = None
    if use_cache:
        data = cache.get(cache_key, None)
    if not data:
        temps = WeatherData.objects.filter(
            timestamp__range=(day, day + timedelta(days=1, seconds=-1))
        ).aggregate(high=Max('outside_temp'), low=Min('outside_temp'))
        summary = MinuteData.objects.filter(
            timestamp__range=(day, day + timedelta(days=1, seconds=-1))
        ).aggregate(watts=Sum('watts'))

        kwhrs = Decimal(summary["watts"]) / Decimal(60000.0) if summary["watts"] else ZERO
        data = {
            "date": day,
            "kwhrs": kwhrs,
            "high": temps["high"],
            "low": temps["low"],
            "high_pct": (Decimal(temps["high"]) / Decimal(1.2) if temps["high"] else ZERO),
            "low_pct": Decimal(temps["low"]) / Decimal(1.2) if temps["low"] else ZERO,
        }
        if use_cache:
            cache.set(cache_key, data)
    return data


def get_daily_data(start_day, end_day=None, today=None):
    if today is None:
        raise RuntimeError("get_daily_data requires 'today'")
    if end_day is None:
        end_day = start_day
    if type(start_day) is not datetime:
        start_day = datetime.combine(start_day, datetime.min.time())
    if type(end_day) is not datetime:
        end_day = datetime.combine(end_day, datetime.min.time())
    if start_day > end_day:
        num_days = 0
    else:
        num_days = (end_day - start_day).days

    today = timezone.now().date()

    day_list = []
    max_kwhrs = Decimal(0.0)
    for day_no in range(0, num_days+1):
        day = start_day + timedelta(days=day_no)
        if day.date() <= today:
            data = get_day_data(day, use_cache=(day.date() < today))
        else:
            data = {
                "date": day, "kwhrs": ZERO, "high": ZERO, "low": ZERO,
                "high_pct": ZERO, "low_pct": ZERO,
            }

        if data["kwhrs"] > max_kwhrs:
            max_kwhrs = data["kwhrs"]

        day_list.append(data)

    for day in day_list:
        day.update({"kwhrs_pct": Decimal(100.0) * day["kwhrs"] / max_kwhrs})

    return day_list


def get_day_type(day):
    """
    Returns the type of "tariff" day for the given date/datetime.
    :param day: Can be of type «date» or «datetime»
    :return: One of constants: {WEEKEND, SUMMER, WINTER}
    """
    if type(day) is not datetime:
        day = datetime.combine(day, datetime.min.time())
    if is_weekend(day) or is_designated_holiday(day):
        return WEEKEND
    elif is_summer(day):
        return SUMMER
    else:
        return WINTER


def categorize_days(start_day, end_day=None):
    """
    Separates the days provided in the range «start_day» to «end_day»
    (inclusive) into three lists:

      1. weekend
      2. summer
      3. winter

    summer and winter are according to Piedmont's schedule, weekend days are
    those on the weekend or Piedmont-designated holidays

    :return: a dict containing 3 lists of dates.
    """
    if end_day is None:
        end_day = start_day

    if type(start_day) is not datetime:
        start_day = datetime.combine(start_day, datetime.min.time())
    if type(end_day) is not datetime:
        end_day = datetime.combine(end_day, datetime.min.time())
    if start_day > end_day:
        num_past_days = 0
    else:
        num_past_days = (end_day - start_day).days

    all_days = {
        WEEKEND: list(),
        SUMMER: list(),
        WINTER: list(),
    }

    for day_no in range(0, num_past_days+1):
        day = start_day + timedelta(days=day_no)
        day_type = get_day_type(day)
        all_days[day_type].append(day)

    return all_days


def get_aggregate_minute_data(days):
    """
    Gets aggregate minute data for the days provided. Uses Memcache to
    cache results.
    """
    empty_hours = [0] * 24
    if days:
        days_str = ",".join([day.strftime("\"%Y-%m-%d\"") for day in days])
        cache_key = safe_cache_key(
            "joule:views:get_aggregate_minute_data:" + days_str)
        today = datetime.combine(datetime.today(), datetime.min.time())
        if today in days:
            wm_hours = None
        else:
            wm_hours = cache.get(cache_key, None)
        if not wm_hours:
            # Initialize a list of 24 zeros
            wm_hours = empty_hours
            cursor = connection.cursor()
            query = """
                SELECT `minute`, AVG(`watts`) FROM `efergy_minutedata`
                WHERE DATE(CONVERT_TZ(`timestamp`, '+00:00', '-04:00')) in (%s)
                GROUP BY `minute`
                ORDER BY `minute`
            """ % (days_str, )
            cursor.execute(query)

            # Add the minute's average consumption (watt-minutes) to the
            # respective hour
            for minute_row in cursor.fetchall():
                hour = minute_row[0] // 60
                wm_hours[hour] = float(wm_hours[hour]) + float(minute_row[1])

            cache.set(cache_key, wm_hours)

        return wm_hours

    return empty_hours


def get_hours(days_dict, tariff, day_counts=None):
    """
    Given a dict of tariff-types and their list of days, return a list of
    tuples, one for each hour [0..23] of the day containing:
        (hour, kwhrs, cost, ext_cost)
    :param days: a dict containing tariff-types and respective list of days.
    :param tariff: A Tariff object
    :param day_counts: A dict containing { tariff-type: num_past_days }, if
                       present is used instead of num of days taken from
                       days_dict.
    :return: a dict containing tariff-types and respective dict of:
             {hour, kwhrs, cost, ext_cost} for each hour.
    """
    all_hours_dict = dict()

    for tariff_type, days in days_dict.items():
        wm_hours = get_aggregate_minute_data(days)

        # Convert from Wm to kWHrs, and to a tuple
        hours = list()
        for hour in range(0, 24):
            wm = wm_hours[hour]
            kwhrs = wm / 60000
            if days:
                timestamp = days[0].replace(hour=hour)
                cost = kwhrs * tariff.rate(timestamp)
            else:
                cost = 0.0
            if day_counts:
                ext_cost = cost * day_counts[tariff_type]
            else:
                ext_cost = cost * len(days)
            hours.append({
                "hour": hour,
                "kwhrs": kwhrs,
                "cost": cost,
                "ext_cost": ext_cost,
            })

        all_hours_dict.update({tariff_type: hours})

    return all_hours_dict


def add_relative_sizes(hours, max_kwhrs, max_cost):
    new_list = []
    for item in hours:
        kwhrs = item["kwhrs"]
        cost = item["cost"]
        item.update({
            "pct_kwhrs": kwhrs / max_kwhrs * 100,
            "pct_cost": cost / max_cost * 100,
        })
        new_list.append(item)
    return new_list


def get_weighted_merge(a, b, a_weight=1, b_weight=1):

    def avg(a, b):
        if not a or not b:
            return max(a, b)
        else:
            return (a * a_weight + b * b_weight) / (a_weight + b_weight)

    cost = avg(a["cost"], b["cost"])
    dict_m = {
        "hour": a["hour"],
        "kwhrs": avg(a["kwhrs"], b["kwhrs"]),
        "cost": cost,
        "ext_cost": cost * (a_weight + b_weight),
    }
    return dict_m


def get_merged_hours(a, b, a_weight=1, b_weight=1):
    """
    Merges list of dicts: «a» and «b» into one respecting their weights:
    «a_weight» and «b_weight»
    """
    hours = {}
    for tariff_type in [WEEKEND, SUMMER, WINTER]:
        merge = partial(get_weighted_merge,
                        a_weight=a_weight[tariff_type],
                        b_weight=b_weight[tariff_type])
        hours[tariff_type] = map(merge, a[tariff_type], b[tariff_type])
    return hours


class BillEstimateView(TemplateView):
    template_name = 'joule/bill.html'
    year = None
    month = None
    active_month = None
    num_trend_days = 0
    today = None
    now = None
    tz = None
    first_month = None
    current_month = False

    def get_first_month(self):
        if not self.first_month:
            first_record = MinuteData.objects.order_by('timestamp').first()
            self.first_month = first_record.timestamp.astimezone(
                get_localzone()).replace(day=1, hour=0, minute=0, second=0,
                                         microsecond=0, tzinfo=None)
        return self.first_month

    # @method_decorator(cache_page(60))
    def dispatch(self, request, *args, **kwargs):
        self.start_time = datetime.now()
        return super(BillEstimateView, self).dispatch(request, *args, **kwargs)

    def get_timezone(self):
        if self.tz is None:
            self.tz = pytz.timezone(
                getattr(settings, "JOULE_TIMEZONE", "America/New_York"))
        return self.tz

    def get(self, request, *args, **kwargs):
        self.now = timezone.now().astimezone(self.get_timezone())
        self.today = self.now.date()

        if "year" in kwargs and "month" in kwargs:
            self.year = int(kwargs["year"])
            self.month = int(kwargs["month"])

        if not (self.year and self.month):
            url = reverse("bill_view", kwargs={
                "year": self.today.year, "month": self.today.month})
            return redirect(to=url)

        self.active_month = datetime(self.year, self.month, 1)

        if self.today.year == self.year and self.today.month == self.month:
            # OK, we're in the middle of this month, so, we'll require some
            # projections. To project the rest of the month, we'll assume a
            # usage profile similar to the previous 7 days. This is guaranteed
            # to contain weekend and non-weekend days.
            #
            # NOTE: During Months October and April, there may be some poor
            # results when the previous week was of one tariff type, and the
            # rest of the month is another.
            self.num_trend_days = 7

        return super(BillEstimateView, self).get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):

        context = super(BillEstimateView, self).get_context_data(**kwargs)
        month_end = self.active_month.replace(
            day=monthrange(self.active_month.year, self.active_month.month)[1])
        active_month_end = self.active_month.replace(
            day=monthrange(self.year, self.month)[1])

        if self.today == month_end:
            self.num_trend_days = 0

        if self.num_trend_days:
            # These are the days we've already measured this month
            past_days = categorize_days(
                self.active_month, self.today)
            # These are the days we'll be projecting
            future_days = categorize_days(
                self.today + timedelta(days=1), month_end)
        else:
            past_days = categorize_days(self.active_month, active_month_end)
            future_days = []

        self.current_month = (
            self.active_month.date() < self.today <= active_month_end.date())
        context["current_month"] = self.current_month
        context["today"] = self.today

        today_type = get_day_type(self.today)

        # How many days of each type?
        # ----------------------------------------------------------------------
        num_past_days = {
            WEEKEND: len(past_days[WEEKEND]),
            SUMMER: len(past_days[SUMMER]),
            WINTER: len(past_days[WINTER]),
        }

        if future_days:
            num_future_days = {
                WEEKEND: len(future_days[WEEKEND]),
                SUMMER: len(future_days[SUMMER]),
                WINTER: len(future_days[WINTER]),
            }
        else:
            num_future_days = {WEEKEND: 0, SUMMER: 0, WINTER: 0}

        num_days = {
            WEEKEND: num_past_days[WEEKEND] + num_future_days[WEEKEND],
            SUMMER: num_past_days[SUMMER] + num_future_days[SUMMER],
            WINTER: num_past_days[WINTER] + num_future_days[WINTER],
        }
        context["num_days"] = num_days

        total_days = sum([num_days[WEEKEND], num_days[SUMMER], num_days[WINTER]])

        past_hours = get_hours(past_days, piedmont_tariff)

        # If we'll be using trend days to project the rest of the month, then
        # prepare the trend hours and blend with the past hours.
        # ----------------------------------------------------------------------
        if self.num_trend_days:
            trend_days = categorize_days(
                self.today - timedelta(days=self.num_trend_days), self.today)
            future_days_count = {
                WEEKEND: len(future_days[WEEKEND]),
                SUMMER: len(future_days[SUMMER]),
                WINTER: len(future_days[WINTER]),
            }
            trend_hours = get_hours(
                trend_days, piedmont_tariff, future_days_count)

            hours = get_merged_hours(
                past_hours, trend_hours, num_past_days, num_future_days)

        # Otherwise, just use the past hours.
        else:
            trend_hours = []
            hours = {
                WEEKEND: past_hours[WEEKEND],
                SUMMER: past_hours[SUMMER],
                WINTER: past_hours[WINTER],
            }

        #
        # Compute sums
        # ----------------------------------------------------------------------
        all_hours = (hours[WEEKEND] + hours[SUMMER] + hours[WINTER])
        max_kwhrs = max([hour["kwhrs"] for hour in all_hours])
        max_cost = max([hour["cost"] for hour in all_hours])

        context["num_past_days"] = num_past_days

        context['weekend_hours'] = add_relative_sizes(hours[WEEKEND], max_kwhrs, max_cost)
        context['summer_hours'] = add_relative_sizes(hours[SUMMER], max_kwhrs, max_cost)
        context['winter_hours'] = add_relative_sizes(hours[WINTER], max_kwhrs, max_cost)

        kwhrs_per_weekend = sum([hour['kwhrs'] for hour in past_hours[WEEKEND]])
        kwhrs_per_summer = sum([hour['kwhrs'] for hour in past_hours[SUMMER]])
        kwhrs_per_winter = sum([hour['kwhrs'] for hour in past_hours[WINTER]])

        est_kwhrs = sum([
            kwhrs_per_weekend * len(past_days[WEEKEND]),
            kwhrs_per_summer * len(past_days[SUMMER]),
            kwhrs_per_winter * len(past_days[WINTER])
        ])

        cost_per_weekend = sum([hour['cost'] for hour in past_hours[WEEKEND]])
        cost_per_summer = sum([hour['cost'] for hour in past_hours[SUMMER]])
        cost_per_winter = sum([hour['cost'] for hour in past_hours[WINTER]])

        energy_cost = sum([cost_per_weekend, cost_per_summer, cost_per_winter])

        ext_cost_per_weekend = sum([hour['ext_cost'] for hour in past_hours[WEEKEND]])
        ext_cost_per_summer = sum([hour['ext_cost'] for hour in past_hours[SUMMER]])
        ext_cost_per_winter = sum([hour['ext_cost'] for hour in past_hours[WINTER]])

        est_energy_cost = sum(
            [ext_cost_per_weekend, ext_cost_per_summer, ext_cost_per_winter])

        if self.num_trend_days:
            kwhrs_per_trend_weekend = sum([hour['kwhrs'] for hour in trend_hours[WEEKEND]])
            kwhrs_per_trend_summer = sum([hour['kwhrs'] for hour in trend_hours[SUMMER]])
            kwhrs_per_trend_winter = sum([hour['kwhrs'] for hour in trend_hours[WINTER]])

            est_kwhrs += sum([
                kwhrs_per_trend_weekend * len(future_days[WEEKEND]),
                kwhrs_per_trend_summer * len(future_days[SUMMER]),
                kwhrs_per_trend_winter * len(future_days[WINTER])
            ])

            kwhrs_per_weekend += kwhrs_per_trend_weekend
            kwhrs_per_summer += kwhrs_per_trend_summer
            kwhrs_per_winter += kwhrs_per_trend_winter

            cost_per_trend_weekend = sum([hour['cost'] for hour in trend_hours[WEEKEND]])
            cost_per_trend_summer = sum([hour['cost'] for hour in trend_hours[SUMMER]])
            cost_per_trend_winter = sum([hour['cost'] for hour in trend_hours[WINTER]])

            ext_cost_per_trend_weekend = sum([hour['ext_cost'] for hour in trend_hours[WEEKEND]])
            ext_cost_per_trend_summer = sum([hour['ext_cost'] for hour in trend_hours[SUMMER]])
            ext_cost_per_trend_winter = sum([hour['ext_cost'] for hour in trend_hours[WINTER]])

            energy_cost += sum([
                cost_per_trend_weekend,
                cost_per_trend_summer,
                cost_per_trend_winter
            ])

            est_energy_cost += sum([
                ext_cost_per_trend_weekend,
                ext_cost_per_trend_summer,
                ext_cost_per_trend_winter
            ])

            ext_cost_per_weekend += ext_cost_per_trend_weekend
            ext_cost_per_summer += ext_cost_per_trend_summer
            ext_cost_per_winter += ext_cost_per_trend_winter

        context['kwhrs_per_weekend'] = kwhrs_per_weekend
        context['kwhrs_per_summer'] = kwhrs_per_summer
        context['kwhrs_per_winter'] = kwhrs_per_winter

        context['ext_cost_per_weekend'] = ext_cost_per_weekend
        context['ext_cost_per_summer'] = ext_cost_per_summer
        context['ext_cost_per_winter'] = ext_cost_per_winter

        context['cost_per_weekend'] = cost_per_weekend
        context['cost_per_summer'] = cost_per_summer
        context['cost_per_winter'] = cost_per_winter

        context['est_kwhrs'] = est_kwhrs
        context['est_energy_cost'] = est_energy_cost

        piedmont_bill.initialize(est_kwhrs, est_energy_cost, total_days)
        context['est_bill'] = piedmont_bill.get_total()

        context['hours'] = range(0, 24)

        context['active_month'] = (self.active_month, active_month_end)

        context['now'] = self.now

        context["temperatures"] = get_daily_data(
            self.active_month, month_end, self.today)

        first_month = self.get_first_month()

        prev_month_end = self.active_month - timedelta(days=1)
        prev_month = prev_month_end.replace(day=1)
        if prev_month >= first_month:
            context['prev_month'] = prev_month

        if (self.now.year != self.active_month.year or
                    self.now.month != self.active_month.month):
            context['next_month'] = active_month_end + timedelta(days=1)

        context['timer'] = datetime.now() - self.start_time

        if self.current_month:
            context['stats'] = get_minute_coverage()

        return context
