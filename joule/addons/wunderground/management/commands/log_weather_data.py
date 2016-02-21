# -*- coding: utf-8 -*-

from __future__ import unicode_literals

from datetime import datetime
from decimal import Decimal
from email import utils

import kronos
import pytz
import requests

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db.utils import IntegrityError

from ...models import WeatherData


def get_data_from_request(req):
    data = req.json()
    timestamp_str = data["current_observation"]["observation_time_rfc822"]
    # Converts the rfc822 timestamp to python datetime objects
    timestamp = datetime.fromtimestamp(
        utils.mktime_tz(utils.parsedate_tz(timestamp_str)), pytz.utc)
    outside_temp = Decimal(data["current_observation"]["temp_f"])
    outside_humidity_str = data["current_observation"]["relative_humidity"]
    outside_humidity = Decimal(outside_humidity_str.replace('%', ''))
    barometric_pressure = Decimal(
        data["current_observation"]["pressure_mb"])
    return {
        "timestamp": timestamp,
        "outside_temp": outside_temp,
        "outside_humidity": outside_humidity,
        "barometric_pressure": barometric_pressure,
    }


@kronos.register("*/30 * * * *")
class Command(BaseCommand):

    help = """Request, parse and store basic weather data.
    """

    def handle(self, *args, **kwargs):
        key = getattr(settings, 'WUNDERGROUND_KEY', None)
        zip_code = getattr(settings, 'WUNDERGROUND_ZIP', None)
        if not key or not zip_code:
            return

        host = "http://api.wunderground.com"
        url = "{host}/api/{key}/conditions/q/{zip_code}.json".format(
            host=host, key=key, zip_code=zip_code)
        r = requests.get(url)
        if r.status_code != 200:
            print("Request for weather data returned status code: {0}".format(
                r.status_code))
            return

        try:
            entry = get_data_from_request(r)
        except ValueError:
            print('Skipping unparsable response')
            return

        try:
            WeatherData.objects.create(**entry)
        except IntegrityError:
            print('Skipping duplicate report for timestamp')
            return

        print(
            "{timestamp}:: Temp: {outside_temp}°F, Pres: "
            "{barometric_pressure}mb, Rel. Hum: {outside_humidity}%".format(
                **entry))
