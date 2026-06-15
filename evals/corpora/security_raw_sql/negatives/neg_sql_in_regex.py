"""Regex patterns that MATCH SQL syntax -- the pattern is not itself SQL.

SQL formatters, query auditors, and migration tools build regexes that
recognise SELECT / INSERT / UPDATE statements. The pattern string contains
SQL keywords but is compiled by ``re``, not executed by a DB driver.
"""

from __future__ import annotations

import re

SELECT_RE = re.compile(r"^\s*SELECT\b", re.IGNORECASE)
INSERT_RE = re.compile(r"^\s*INSERT\s+INTO\s+\w+", re.IGNORECASE)
UPDATE_RE = re.compile(r"^\s*UPDATE\s+\w+\s+SET\b", re.IGNORECASE)
DELETE_RE = re.compile(r"^\s*DELETE\s+FROM\s+\w+", re.IGNORECASE)


def is_select(sql: str) -> bool:
    return bool(SELECT_RE.match(sql))


def find_tables(sql: str):
    return re.findall(r"\bFROM\s+(\w+)", sql, flags=re.IGNORECASE)


def strip_create_index(sql: str) -> str:
    return re.sub(r"CREATE\s+INDEX\s+\w+\s+ON\s+\w+\s*\([^)]*\);?", "", sql, flags=re.IGNORECASE)


def detect_dml(sql: str) -> str | None:
    if re.match(r"^\s*(INSERT|UPDATE|DELETE)\b", sql, re.IGNORECASE):
        return "dml"
    return None


def split_statements(blob: str):
    return re.split(r";\s*(?=SELECT|INSERT|UPDATE|DELETE|CREATE|DROP|ALTER)", blob, flags=re.IGNORECASE)
