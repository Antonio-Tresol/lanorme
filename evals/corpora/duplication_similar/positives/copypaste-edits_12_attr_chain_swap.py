# why: positive - aggregation pair where a single attribute in a chain differs (.gross vs .nett) and one debug append was dropped; copy-paste drift.
from __future__ import annotations


def total_gross_by_region(orders):
    buckets = {}
    counted = 0
    trace = []
    for order in orders:
        region = order.customer.region
        buckets.setdefault(region, 0)
        buckets[region] += order.gross
        counted += 1
        trace.append(order.identifier)
    ranked = sorted(buckets.items(), key=lambda pair: pair[1], reverse=True)
    return ranked


def total_nett_by_region(orders):
    buckets = {}
    counted = 0
    for order in orders:
        region = order.customer.region
        buckets.setdefault(region, 0)
        buckets[region] += order.nett
        counted += 1
    ranked = sorted(buckets.items(), key=lambda pair: pair[1], reverse=True)
    return ranked
