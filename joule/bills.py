#  -*- coding: utf-8 -*-

from __future__ import unicode_literals


class BillModifier(object):
    def __init__(self, label=""):
        self.label = label

    def __str__(self):
        return self.label or "modifier"


class Rider(BillModifier):
    """
    A "rider" modifies the bill by a "rate" or factor of the consumed kWHrs.
    """
    def __init__(self, label="", rate=0.0):
        super(Rider, self).__init__(label)
        self.rate = rate

    def get_amount(self, kwhrs=0.0):
        return kwhrs * self.rate


class Fee(BillModifier):
    """
    A "fee" is a flat cost added to the bill, it is not dependent on the kWHrs
    consumed, but may be a factor of the number of days.
    """
    def __init__(self, label="", factor=0.0, daily=False):
        super(Fee, self).__init__(label)
        self.factor = factor
        self.daily = daily

    def get_amount(self, days=0.0):
        if self.daily:
            return days * self.factor
        else:
            return self.factor


class Tax(BillModifier):
    """
    A "tax" modifies the bill by a "rate" of the subtotal (untaxed cost).
    """

    def __init__(self, label="", rate=0.0):
        super(Tax, self).__init__(label)
        self.rate = rate

    def get_amount(self, subtotal=0.0):
        return subtotal * self.rate


class Bill:
    """
    Encapsulates the concept of a monthly electric bill.
    """
    kwhrs = 0.0
    energy_cost = 0.0
    days = 0

    def __init__(self, fees=(), riders=(), taxes=(), agg_data=None):
        self.fees = fees
        self.riders = riders
        self.taxes = taxes
        self.agg_data = agg_data

    def get_subtotal(self, energy_cost=0.0, kwhrs=0.0, days=0):
        energy_cost = energy_cost or self.energy_cost
        kwhrs = kwhrs or self.kwhrs
        days = days or self.days

        subtotal = energy_cost

        for fee in self.fees:
            subtotal += round(fee.get_amount(days), 2)

        for rider in self.riders:
            subtotal += round(rider.get_amount(kwhrs), 2)

        return subtotal

    def get_total(self, energy_cost=0.0, kwhrs=0.0, days=0):
        energy_cost = energy_cost or self.energy_cost
        kwhrs = kwhrs or self.kwhrs
        days = days or self.days

        subtotal = self.get_subtotal(energy_cost, kwhrs, days)
        total = subtotal

        for tax in self.taxes:
            total += round(tax.get_amount(subtotal), 2)

        return total

    def get_bill(self, energy_cost=0.0, kwhrs=0.0, days=0):
        energy_cost = energy_cost or self.energy_cost
        kwhrs = kwhrs or self.kwhrs
        days = days or self.days

        max_len = 0
        for modifier in self.fees + self.riders + self.taxes:
            label_len = len(modifier.label)
            if label_len > max_len:
                max_len = label_len

        subtotal = self.get_subtotal(energy_cost, kwhrs, days)
        total = self.get_total(energy_cost, kwhrs, days)

        money_row = "{{label:{0}s}} ${{amount:6.2f}}".format(max_len)
        energy_row = "{{label:{0}s}} {{amount:7.3f}}".format(max_len)
        subtotal_rule = "-" * (max_len + 8)
        total_rule = "=" * (max_len + 8)

        output = ""

        output += energy_row.format(
            label="Energy Used (kWHrs)", amount=kwhrs) + "\n"

        output += money_row.format(
            label="Energy Cost", amount=energy_cost) + "\n"

        for fee in self.fees:
            output += money_row.format(
                label=str(fee), amount=fee.get_amount(days=days)) + "\n"

        for rider in self.riders:
            output += money_row.format(
                label=str(rider), amount=rider.get_amount(kwhrs=kwhrs)) + "\n"
        output += subtotal_rule + "\n"
        output += money_row.format(label="Subtotal", amount=subtotal) + "\n"

        for tax in self.taxes:
            output += money_row.format(
                label=str(tax), amount=tax.get_amount(subtotal=subtotal)) + "\n"

        output += total_rule + "\n"
        output += money_row.format(label="Total", amount=total)

        return output
