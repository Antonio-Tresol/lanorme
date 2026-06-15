"""Inline restating comments (trailing the code on the same line).

The current detector only inspects standalone comments, so these are
ground-truth positives it is guaranteed to miss.
"""

from __future__ import annotations


def run(counter: int, items: list[int], name: str, total: int) -> int:
    counter += 1  # increment counter
    total = total + counter  # add counter to total
    name = name.strip()  # strip the name
    items.sort()  # sort items
    items.reverse()  # reverse the items
    return total  # return total


def reset(state: dict[str, int]) -> None:
    state.clear()  # clear the state
    state["count"] = 0  # set count to zero


def fetch(cache: dict[str, int], key: str) -> int:
    return cache[key]  # return cache value for key
