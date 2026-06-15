# why: positive - two query builders copy-pasted; they differ only by the
# why: keyword-argument names handed to the filter call. DRY-001 misses kwarg
# why: drift, but a reviewer would collapse these into one parametrised query.
"""Two list helpers differing only by keyword-argument names on a filter call."""

from __future__ import annotations


def list_open_tickets(session, owner):
    query = session.query("ticket")
    query = query.filter(assignee=owner, archived=False)
    query = query.order_by("created")
    rows = query.all()
    return [r.to_dict() for r in rows]


def list_open_tasks(session, owner):
    query = session.query("ticket")
    query = query.filter(responsible=owner, closed=False)
    query = query.order_by("created")
    rows = query.all()
    return [r.to_dict() for r in rows]
