# -*- coding: utf-8 -*_

from __future__ import unicode_literals

import hashlib

from datetime import datetime

from django.conf import settings


def safe_cache_key(value):
    """
    Returns an md5 hexdigest of value if len(value) > 250. Replaces invalid
    memcache control characters with an underscore. Also adds the
    CACHE_MIDDLEWARE_KEY_PREFIX to your keys automatically.
    """
    for char in value:
      if ord(char) < 33:
          value = value.replace(char, '_')

    value = "%s_%s" % (settings.CACHE_MIDDLEWARE_KEY_PREFIX, value)

    if len(value) <= 250:
        return value

    m = hashlib.md5()
    m.update(value)
    return m.hexdigest()


class Timer(object):

    def __enter__(self):
        self.start = datetime.now()
        return self

    def __exit__(self, *args):
        self.end = datetime.now()
        self.interval = self.end - self.start


class MemoizeByKeyFunc(object):
    """
    Acts as a memoize decorator, but you can optionally pass a callable that
    determines the memoization key from the provided arguments. For example,
    wrapping the following with a traditional memoize decorator:

        @memoize
        def expensive_compute_from_date(timestamp):
            ...

    Would be rather ineffectual if input is expected to be any time of any
    day, because it is only the date-portion of the timestamp that has any
    effect on the output. Memoizing on just the date portion alone is ideal.

    To gain this improvement, pass a callable as «key_func» that returns only
    the date portion of a given timestamp, a la:

        @MemoizeByKeyFunc(key_func=lambda x: x.date())
        def expensive_compute_from_date(timestamp):
            ...

    Now, the internal cache for storing pre-computed values will get hit quite a
    bit saving a lot of recalculation. And, it will contain many fewer entries.

    :param key_func: A callable that accepts *args, returns the memoization key.
    :returns: Wrapped function
    """
    def identity_func(*args):
        """
        Simple function that returns whatever arguments it receives.
        """
        return args[0] if len(args) == 1 else args

    def __init__(self, key_func=identity_func):
        """
        The identity_func default allows this decorator to be called without an
        explicit callable, in which case, this will function as a more normal
        memoize decorator too.
        """
        self.key_func = key_func
        self.memoized = dict()

    def __call__(self, func):
        def wrapped_func(*args):
            key = self.key_func(*args)
            try:
                return self.memoized[key]
            except KeyError:
                self.memoized[key] = func(*args)
                return self.memoized[key]
        return wrapped_func

memoize_by_key_func = MemoizeByKeyFunc
