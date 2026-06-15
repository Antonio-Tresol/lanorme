#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tooling pragmas: linter/type directives, not human prose."""

from __future__ import annotations

import os  # noqa: F401
from typing import Any


def coerce(value: Any) -> int:
    result = int(value)  # type: ignore[arg-type]
    return result


def legacy(data):  # noqa: ANN001
    return data


def disable_block() -> None:
    # fmt: off
    matrix = [
        1, 0, 0,
        0, 1, 0,
    ]
    # fmt: on
    return matrix


def typed() -> "list[int]":
    x = []  # type: list[int]
    return x


GLOBAL = {}  # pylint: disable=invalid-name
