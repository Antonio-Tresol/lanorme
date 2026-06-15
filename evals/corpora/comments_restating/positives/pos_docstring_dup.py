"""Docstring-vs-comment redundancy.

Each `#` comment paraphrases a sentence already present in the enclosing
function or class docstring. The docstring is the source of truth, so the
comment is redundant and should be flagged as restating.
"""

from __future__ import annotations


def add(a: int, b: int) -> int:
    """Return the sum of a and b."""
    # returns the sum of a and b
    return a + b


def fetch(url: str) -> str:
    """Fetch the URL and return the response body as text.

    The request times out after 30 seconds.
    """
    # fetch the URL and return the response body as text
    return ""


def normalize(name: str) -> str:
    """Lowercase the name and strip surrounding whitespace."""
    # lowercases the name and strips surrounding whitespace
    return name.strip().lower()


class Cache:
    """In-memory LRU cache with a fixed capacity of 128 entries."""

    def __init__(self) -> None:
        # in-memory LRU cache with a fixed capacity of 128 entries
        self._data: dict[str, int] = {}


def divide(a: int, b: int) -> float:
    """Divide a by b. Raises ZeroDivisionError when b is zero."""
    # divide a by b; raises ZeroDivisionError when b is zero
    return a / b
