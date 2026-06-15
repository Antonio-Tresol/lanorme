"""Type-spelled-in-prose restatements.

Each comment restates a type or shape that is already declared in the
adjacent type hint. The type hint is the source of truth; the comment adds
nothing. Should be flagged as restating.
"""

from __future__ import annotations


def names() -> list[str]:
    # returns a list of strings
    return ["a", "b"]


def lookup_age(name: str) -> int | None:
    # returns an int or None
    return None


def headers() -> dict[str, str]:
    # returns a dict mapping strings to strings
    return {"a": "b"}


def coordinates() -> tuple[float, float]:
    # returns a tuple of two floats
    return (0.0, 0.0)


def labels() -> set[str]:
    # returns a set of strings
    return {"x"}


def find(name: str) -> str | None:
    # returns a string or None
    return None
