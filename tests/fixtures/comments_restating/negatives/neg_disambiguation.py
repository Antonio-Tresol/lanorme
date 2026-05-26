"""Disambiguation of subtle code: clarifies non-obvious behaviour."""

from __future__ import annotations


def trim(values: list[int]) -> list[int]:
    # Slice copies; mutating the result will not touch the original.
    return values[1:-1]


def midpoint(lo: int, hi: int) -> int:
    # Written this way to avoid integer overflow on huge bounds.
    return lo + (hi - lo) // 2


def first_true(flags: list[bool]) -> int:
    # next() with a default avoids a StopIteration when all are False.
    return next((i for i, f in enumerate(flags) if f), -1)


def truthy_default(value, fallback):
    # "or" picks the fallback for any falsy value, not just None.
    return value or fallback


def shallow(config: dict) -> dict:
    # Deliberately a shallow copy: nested dicts stay shared by design.
    return dict(config)


def floor_div(a: int, b: int) -> int:
    # Python floors toward negative infinity, unlike C truncation.
    return a // b
