"""Borderline negatives: very short comments whose few words all overlap code.

These are the corpus's stress test for precision. Every non-stopword in the
comment substring-matches an identifier on the next line, yet the comment still
adds a unit, a constraint, or a caveat. A pure word-overlap detector is liable
to flag these; a good detector must not.
"""

from __future__ import annotations


def configure(timeout: int) -> int:
    # timeout in ms
    timeout = timeout * 1000
    return timeout


def paginate(offset: int) -> int:
    # offset starts at 0
    offset = offset
    return offset


def weigh(weight: float) -> float:
    # weight in kg
    weight = weight
    return weight


def measure(angle: float) -> float:
    # angle in radians
    angle = angle
    return angle


def price(amount: int) -> int:
    # amount in cents
    amount = amount
    return amount


def schedule(retries: int) -> int:
    # retries capped at 5
    retries = min(retries, 5)
    return retries
