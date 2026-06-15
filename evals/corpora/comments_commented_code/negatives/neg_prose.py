"""Explanatory prose comments ending in sentence punctuation."""

from __future__ import annotations


def retry(fn, attempts: int = 3):
    # We retry on transient network failures only, never on validation errors.
    # The caller is expected to handle non-retryable exceptions itself.
    # Is three the right number? Empirically yes for our p99 latency budget.
    # Do not lower this without checking the deploy dashboard first!
    for _ in range(attempts):
        try:
            return fn()
        except ConnectionError:
            continue
    raise RuntimeError("exhausted retries")


def cache_get(key: str):
    # The cache may return stale values during failover windows.
    # Callers that require strong consistency should bypass this layer.
    return _STORE.get(key)


_STORE: dict[str, object] = {}
