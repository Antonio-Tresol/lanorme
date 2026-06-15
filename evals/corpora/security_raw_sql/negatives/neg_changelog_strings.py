"""CHANGELOG / release-note style strings mentioning SQL operations.

Release notes, migration descriptions, and ops runbooks live in Python as
data (lists of strings, dict values) and frequently mention SELECTs or
DROPs they enabled or removed. They are display strings, not payloads.
"""

from __future__ import annotations


CHANGELOG = [
    "v1.4.0 -- replaced raw SELECT in user_repo with ORM query",
    "v1.3.2 -- removed dangerous DROP TABLE temp_audit from teardown",
    "v1.3.1 -- added ALTER TABLE migration for the new locale column",
    "v1.2.0 -- introduced INSERT batching for the events pipeline",
]


RELEASE_NOTES = {
    "1.4.0": "Refactored the dashboard SELECT to use the ORM",
    "1.3.0": "Removed CREATE TEMP TABLE usage from analytics job",
    "1.2.0": "Migrated DELETE FROM stale_sessions to a scheduled job",
}


def format_release(version):
    return f"Release {version}: replaced raw UPDATE with bound parameters"


RUNBOOK = """
On-call: if the dashboard query (a SELECT joining payments and users) starts
timing out, run a CREATE INDEX on payments(paid_at) and re-check.
"""


def banner():
    return "This release deprecates the raw DROP / TRUNCATE helpers."
