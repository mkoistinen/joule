# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import tablib
import pytz

from datetime import datetime
from decimal import Decimal, InvalidOperation

from django.db.utils import IntegrityError
from django.core.management.base import BaseCommand
from django.utils import timezone

from ...models import MinuteData


def make_timestamp(date_string):
    """
    A row-operation that converts an Efergy timestamp of the form
    "2015-12-31 12:34:56" into a Python datetime object.
    """
    try:
        return datetime.strptime(date_string, '%Y-%m-%d %H:%M:%S')
    except:
        return None


class Command(BaseCommand):
    help = """Load Efergy's Engage minute data directly in like this:
        `python.py manage load_engage_data your_filename.csv`
    """

    def add_arguments(self, parser):
        parser.add_argument('file_name', nargs='+', type=str)

    def handle(self, *args, **options):
        file_name = options['file_name'][0]
        data = tablib.Dataset()
        data.csv = open(file_name).read()
        counter = 0

        for row in data:
            timestamp = timezone.make_aware(
                make_timestamp(row[0]), timezone.get_current_timezone())
            try:
                value = Decimal(row[1])
            except InvalidOperation:
                value = None

            if timestamp and value:
                minute = timestamp.hour * 60 + timestamp.minute
                try:
                    MinuteData.objects.create(
                        # TODO: Obviously, this should be a setting somewhere
                        timestamp=timestamp.astimezone(
                            pytz.timezone("America/New_York")),
                        minute=minute,
                        watts=value
                    )
                    counter += 1
                except IntegrityError:
                    pass

        print('Imported {0} new minutes from {1}'.format(counter, file_name))
