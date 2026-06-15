"""Warnings, invariants and gotchas: critical information, never restatement."""

from __future__ import annotations

import threading

_lock = threading.Lock()


def bisect_left(data: list[int], target: int) -> int:
    # Caller must pass a sorted list; results are undefined otherwise.
    lo, hi = 0, len(data)
    while lo < hi:
        mid = (lo + hi) // 2
        if data[mid] < target:
            lo = mid + 1
        else:
            hi = mid
    return lo


def update(shared: dict[str, int], key: str) -> None:
    # Not thread-safe: hold _lock before calling from multiple threads.
    shared[key] = shared.get(key, 0) + 1


def scale(value: float) -> float:
    # WARNING: overflows for inputs above 1e308; clamp upstream.
    return value * 1e10


def divide(a: float, b: float) -> float:
    # Precondition: b is guaranteed non-zero by the schema validator.
    return a / b


def render(template: str) -> str:
    # Danger: this trusts the template; never pass user input here.
    return eval(template)  # noqa: S307
