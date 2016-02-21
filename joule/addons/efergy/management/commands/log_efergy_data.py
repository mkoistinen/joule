# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import sys

from datetime import datetime
from decimal import Decimal, InvalidOperation
from threading import Thread
from Queue import Queue, Empty

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db.utils import IntegrityError

from ...models import EfergyData


def parse_line(line):
    """
    Given a log-line, convert to native datetime and Decimal formats.
    """
    date_str, time_str, watts_str = line.split(',')
    timestamp = datetime.strptime(
        date_str + "|" + time_str, "%m/%d/%y|%H:%M:%S")
    timestamp = timezone.make_aware(timestamp, timezone.get_current_timezone())
    watts = Decimal(watts_str)
    return {'timestamp': timestamp, 'watts': watts}


class NonBlockingStreamReader:

    def __init__(self, stream):
        """
        stream: the stream to read from.
                Usually a process' stdout or stderr.
        """

        self._s = stream
        self._q = Queue()

        def _populate_queue(stream, queue):
            """
            Collect lines from 'stream' and put them in 'quque'.
            """

            while True:
                line = stream.readline()
                if line:
                    queue.put(line)
                else:
                    raise UnexpectedEndOfStream

        self._t = Thread(target=_populate_queue, args=(self._s, self._q))
        self._t.daemon = True
        self._t.start()  # start collecting lines from the stream

    def read_line(self, timeout=None):
        try:
            return self._q.get(block=timeout is not None, timeout=timeout)
        except Empty:
            return None


class UnexpectedEndOfStream(Exception):
    pass


class Command(BaseCommand):

    help = """Pipe Efergy data directly in like this:
        `cat efergy_data.log | python manage.py log_efergy_data`
    """

    def handle(self, *args, **kwargs):
        if not sys.stdin.isatty():
            input_stream = NonBlockingStreamReader(sys.stdin)
        else:
            print(self.help)
            return

        while True:
            line = input_stream.read_line(0.1)
            if line:
                try:
                    entry = parse_line(line)
                except ValueError:
                    print('Skipping unparsable line: {0}.'.format(line))
                    continue

                try:
                    EfergyData.objects.create(**entry)
                except IntegrityError:
                    # Ignore duplicate entries
                    print('Skipping duplicate: {watts} @ {timestamp}'.format(**entry))
                except InvalidOperation:
                    print('Skipping bogus data {watts} @ {timestamp}'.format(**entry))
