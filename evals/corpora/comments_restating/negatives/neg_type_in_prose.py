"""Type-in-prose negatives.

Surface form mirrors the positive twin (the comment names the return type),
but each comment adds a property the type hint does NOT encode: sort order,
non-emptiness, a unit, an ownership rule, or a uniqueness guarantee. These
should NOT be flagged.
"""

from __future__ import annotations


def names() -> list[str]:
    # returns a list of strings, sorted ascending by locale
    return ["a", "b"]


def lookup_age(name: str) -> int | None:
    # returns an int in years; None means the record exists but age is withheld
    return None


def headers() -> dict[str, str]:
    # returns a dict mapping lowercased header names to their first value only
    return {"a": "b"}


def coordinates() -> tuple[float, float]:
    # returns (latitude, longitude) in WGS84 degrees
    return (0.0, 0.0)


def labels() -> set[str]:
    # returns a set of strings; the caller may mutate it freely (fresh copy)
    return {"x"}


def find(name: str) -> str | None:
    # returns a string interned in the global pool; identity-comparison-safe
    return None
