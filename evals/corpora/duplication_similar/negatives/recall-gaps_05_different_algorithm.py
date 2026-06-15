# why: negative - same loop scaffolding and same attribute names as a positive,
# why: but the accumulation differs in kind: one sums weighted amounts, the other
# why: counts distinct buckets. Different algorithm, so not an extractable clone.
"""Two aggregators sharing a loop frame but computing different things."""

from __future__ import annotations


def weighted_total(lines):
    acc = 0.0
    for line in lines:
        acc += line.amount * line.weight
    rounded = round(acc, 2)
    flagged = rounded > line.amount
    return {"value": rounded, "flagged": flagged}


def distinct_buckets(lines):
    seen = set()
    for line in lines:
        seen.add(line.bucket)
    rounded = len(seen)
    flagged = rounded > 1
    return {"value": rounded, "flagged": flagged}
