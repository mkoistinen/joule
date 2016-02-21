#  -*- coding: utf-8 -*-

from __future__ import unicode_literals

from functools import partial

from datetime import datetime, timedelta

from . import *
from .bills import Bill, Fee, Rider, Tax
from .tariffs import (
    RateModifier, Tariff,
    always, is_hour_of_day, is_weekday,
)
from .utils import memoize_by_key_func


is_1pm_to_6pm = partial(is_hour_of_day, hours=[13, 14, 15, 16, 17])
is_6am_to_10am = partial(is_hour_of_day, hours=[6, 7, 8, 9])


@memoize_by_key_func(key_func=lambda x: x.date() if hasattr(x, "date") else x)
def is_designated_holiday(timestamp):
    """
    Returns True if the date is one of Piedmont’s "designated holidays":
    - New Years Day (January 1st)
    - Memorial Day (last Monday of May)
    - Independence Day (July 4th)
    - Labor Day (First Monday of September)
    - Thanksgiving Day (4th Thursday in November)
    - Christmas Day (December 25th)
    """
    dow = timestamp.weekday()
    day = timestamp.day
    month = timestamp.month

    if month == JANUARY and timestamp.day == 1:
        return True
    elif month == MAY and dow == MONDAY and day > 25:
        return True
    elif month == JULY and day == 4:
        return True
    elif month == SEPTEMBER and dow == MONDAY and day < 8:
        return True
    elif month == NOVEMBER and dow == THURSDAY and 21 < day < 29:
        return True
    elif month == DECEMBER and day == 25:
        return True
    else:
        return False


@memoize_by_key_func(key_func=lambda x: x.year)
def summer_start(timestamp):
    """
    Returns 00:00:01 on the Sunday following the 2nd Saturday of April for
    the year given in «timestamp», which is the end of Piedmont's Summer period.
    """
    year = timestamp.year
    apr_7th = datetime(year=year, month=4, day=7, second=1)
    dow = apr_7th.weekday()
    if dow == SUNDAY:
        return apr_7th + timedelta(days=7)
    elif dow == SATURDAY:
        return apr_7th + timedelta(days=8)
    else:
        return apr_7th + timedelta(days=(7-dow))


@memoize_by_key_func(key_func=lambda x: x.year)
def summer_end(timestamp):
    """
    Returns 00:00:00 on the 2nd Saturday of October, which is the end of
    Piedmont's Summer period.
    """
    year = timestamp.year
    oct_7th = datetime(year=year, month=10, day=7)
    dow = oct_7th.weekday()
    if dow == SUNDAY:
        return oct_7th + timedelta(days=6)
    elif dow == SATURDAY:
        return oct_7th + timedelta(days=7)
    else:
        return oct_7th + timedelta(days=(6-dow))


def is_summer(timestamp):
    """
    Returns True if timestamps is within the Summer season as defined by
    Piedmont Electic Coop.

    Returns True if timestamp is within:

        00:00:01 on the Sunday following the second Saturday of April through
        00:00:00 on the second Saturday of October

    else False.
    """
    return summer_start(timestamp) <= timestamp < summer_end(timestamp)


def is_winter(timestamp):
    """
    Returns True if the date provided in «timestamp» is within the Winter season
    as defined by Piedmont energy (See is_summer()).
    """
    return not is_summer(timestamp)


def is_summer_peak_hour(timestamp):
    """
    Returns True if «timestamp» is during the defined Summer peak hours on a
    non-holiday weekday.
    """
    return (
        is_1pm_to_6pm(timestamp) and
        is_weekday(timestamp) and not is_designated_holiday(timestamp) and
        is_summer(timestamp)
    )


def is_winter_peak_hour(timestamp):
    """
    Returns True if «timestamp» is during the defined Winter peak hours on a
    non-holiday weekday.
    """
    return (
        is_6am_to_10am(timestamp) and
        is_weekday(timestamp) and not is_designated_holiday(timestamp) and
        is_winter(timestamp)
    )


# Creates the Piedmont Time of Day Energy Only Tariff
piedmont_tariff = Tariff(modifiers=[
    RateModifier(always, 0.0499),
    RateModifier(is_summer_peak_hour, 0.3369 - 0.0499),
    RateModifier(is_winter_peak_hour, 0.2642 - 0.0499),
])


class PiedmontBill(Bill):
    def initialize(self, kwhrs, energy_cost, num_days):
        self.kwhrs = kwhrs
        self.energy_cost = energy_cost
        self.days = num_days

piedmont_bill = PiedmontBill(
    fees=[
        Fee(label="Connection Fee", factor=35.00),
        Fee(label="Security Light Charge", factor=0.3435, daily=True),
        Fee(label="Security Light PCA Charge", factor=-0.0087, daily=True),
    ],
    riders=[
        Rider(label="NC Power Cost Adjustment", rate=-0.005),
        Rider(label="NC Energy Efficiency Rider", rate=0.0005),
        Rider(label="NC Renewable Energy Rider", rate=0.0004),
    ],
    taxes=[
        Tax(label="NC Sales Tax", rate=0.0700625)
    ],
)
