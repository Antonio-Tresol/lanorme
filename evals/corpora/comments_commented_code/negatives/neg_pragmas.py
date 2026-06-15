"""Tool/linter pragma comments consumed by other tools."""

from __future__ import annotations

import os  # noqa: F401
from typing import Any  # noqa: F401


def cast_any(x):
    return x  # type: ignore[return-value]


def legacy(a, b):  # type: (int, int) -> int
    return a + b


def unreliable():
    return 1  # nosec B101
    # pylint: disable=unreachable
    # mypy: ignore-errors
    # ruff: noqa: E501
    # fmt: off
    # fmt: on
    # pragma: no cover
    # coverage: ignore
