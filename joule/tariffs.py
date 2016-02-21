#  -*- coding: utf-8 -*-

from __future__ import unicode_literals

from functools import partial

from . import *


def is_day_of_week(timestamp, days=None):
    if days is None:
        days = []
    if not hasattr(days, '__iter__'):
        days = [days]
    return timestamp.weekday() in days


def is_hour_of_day(timestamp, hours=None):
    if hours is None:
        hours = []
    if not hasattr(hours, '__iter__'):
        hours = [hours]
    return timestamp.hour in hours


def always(*arg, **kwargs):
    return True

is_weekday = partial(is_day_of_week,
                     days=[MONDAY, TUESDAY, WEDNESDAY, THURSDAY, FRIDAY])
is_weekend = partial(is_day_of_week,
                     days=[SATURDAY, SUNDAY])


class RateModifier:
    """
    Creates a callable that returns a rate based on a condition.
    """
    def __init__(self, condition=None, active=0.0, inactive=0.0):
        """
        :param condition: A Callable that returns True or False when given a
                          timestamp as a sole parameter
        :param active:    The value to return when «condition» is True
        :param inactive:  The value to return when «condition» is False
        :return:          «active» if «condition» else «inactive»
        """
        self.condition = condition
        self.active = active
        self.inactive = inactive

    def __call__(self, timestamp):
        if self.condition(timestamp):
            return self.active
        else:
            return self.inactive


class Tariff:
    """
    A collection of RateModifiers that when summed, determines the cost of
    electricity per kWHr for any given moment.
    """
    _list = list()

    def __init__(self, modifiers=()):
        for modifier in modifiers:
            self.add_rate_modifier(modifier)

    def remove_rate_modifier(self, item):
        if item in self._list:
            del self._list[item]

    def add_rate_modifier(self, modifier=None):
        if not isinstance(modifier, RateModifier):
            raise Exception('Only RateModifiers can be added to a Tariff.')
        self._list.append(modifier)

    def get_rate_modifiers(self):
        return self._list

    def rate(self, timestamp):
        return sum([modifier(timestamp) for modifier in self._list])

    def print_modifiers(self):
        for modifier in self._list:
            print("When «{func}», add {active:0.2f}¢{inactive}.".format(
                func=modifier.condition.__name__,
                active=modifier.active*100.0,
                inactive=" else add {0:02f}¢".format(
                    modifier.inactive*100.0) if modifier.inactive else "",
            ))
