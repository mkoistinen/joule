# -*- coding: utf-8 -*-

from __future__ import unicode_literals

from django import template
from django.template import Variable, VariableDoesNotExist
from django.utils.safestring import mark_safe
register = template.Library()


@register.assignment_tag()
def get(list_obj, idx):
    try:
        return list_obj[idx]
    except:
        return None


@register.filter(is_safe=True)
def float_format(value, args):
    """
    Acts a bit like the built-in «floatformat» but takes a pair of numbers as a
    string as the argument. These two numbers define the length of the number on
    the left and the right of the decimal point.

    When the number on the left of the decimal point needs padding, it is padded
    with a "0", but each ZERO is wrapped with a span with the class
    "leading-ZERO", which can be made non-visible if desired.
    """
    if args is None:
        return False
    args_list = [int(arg.strip()) for arg in args.split(',')]
    if len(args_list) != 2:
        return False
    left, right = args_list

    fmt = "{{value:{digits}.{right}f}}".format(
        digits=left + right + 1, right=right)
    ret = fmt.format(value=value)
    ret = mark_safe(ret.replace(' ', '<span class="leading-zero">0</span>'))
    return ret
