"""Hardest negatives: comments that share words with the code but add meaning.

These are the false positives a naive word-overlap detector is most likely to
produce. Each comment reuses an identifier from the next line, yet supplies a
constraint, unit, source, or caveat that the code itself does not state.
"""

from __future__ import annotations

import uuid


def make_id():
    # id must stay a UUIDv4 for the audit log to accept it
    new_id = uuid.uuid4()
    return new_id


def set_timeout(timeout: int) -> int:
    # timeout is in milliseconds, not seconds
    timeout = timeout
    return timeout


def apply_offset(offset: int) -> int:
    # offset is zero-based; the API is one-based
    offset = offset
    return offset


def pick_port() -> int:
    # port 0 lets the OS choose a free one
    port = 0
    return port


def set_count(count: int) -> int:
    # count excludes soft-deleted rows
    count = count
    return count


def retry_after(delay: int) -> int:
    # delay doubles every attempt elsewhere; this is the seed
    delay = delay
    return delay


def cache_value(cache: dict, key: str, value: int) -> None:
    # cache survives only until the next deploy
    cache[key] = value


def total_sum(total: int) -> int:
    # total may briefly go negative during reconciliation
    total = total
    return total
