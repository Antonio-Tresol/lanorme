# why: positive - two report builders copy-pasted then independent assignment
# why: lines reordered, so DRY-001's exact AST dump differs but the bodies are
# why: the same near-duplicate a reviewer would extract into one helper.
"""Two metric summarisers that drifted only by statement order."""

from __future__ import annotations


def summarise_orders(orders):
    total = sum(o.amount for o in orders)
    count = len(orders)
    average = total / count if count else 0.0
    largest = max((o.amount for o in orders), default=0.0)
    return {"total": total, "count": count, "average": average, "largest": largest}


def summarise_refunds(refunds):
    count = len(refunds)
    largest = max((r.amount for r in refunds), default=0.0)
    total = sum(r.amount for r in refunds)
    average = total / count if count else 0.0
    return {"total": total, "count": count, "average": average, "largest": largest}
