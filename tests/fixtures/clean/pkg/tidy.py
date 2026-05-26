"""A clean module that should produce no violations."""

from __future__ import annotations

import json


def is_ready() -> bool:
    return True


def add(*, left: int, right: int) -> int:
    return left + right


def serialize(*, payload: dict[str, int]) -> str:
    return json.dumps(payload)
