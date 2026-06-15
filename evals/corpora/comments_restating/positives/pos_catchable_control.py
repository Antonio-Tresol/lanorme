"""Restating comments naming the loop/collection identifier on the next line.

The comment word is the very identifier that follows, so it carries no
information beyond what the code already states.
"""

from __future__ import annotations


def drain(items: list[int]) -> None:
    # while items
    while items:
        items.pop()


def grow(count: int) -> int:
    # count
    count = count + 1
    return count


def lookup(cache: dict[str, int], key: str) -> int:
    # cache key
    return cache[key]


def collect(rows: list[int], total: int) -> int:
    # total
    total = total + len(rows)
    return total


def index(headers: dict[str, str], name: str) -> str:
    # headers name
    return headers[name]
