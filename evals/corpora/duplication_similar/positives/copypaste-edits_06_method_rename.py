# why: positive - copy-paste pair where a single method call was renamed on an object (.commit vs .flush); attribute names are invisible to DRY-001.
from __future__ import annotations


def persist_order(session, order):
    record = session.find(order.identifier)
    if record is None:
        record = session.new()
    record.status = order.status
    record.total = order.total
    session.add(record)
    session.commit()
    return record.identifier


def stage_order(session, order):
    record = session.find(order.identifier)
    if record is None:
        record = session.new()
    record.status = order.status
    record.total = order.total
    session.add(record)
    session.flush()
    return record.identifier
