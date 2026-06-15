# why: positive - two guard-clause validators, identical checks but the
# why: independent early-return blocks were pasted in a different order, so
# why: DRY-001's exact-dump miss; the dedupe target is one shared validator.
"""Two field validators that differ only in the order of independent guards."""

from __future__ import annotations


def validate_user_payload(payload):
    errors = []
    if not payload.get("name"):
        errors.append("name is required")
    if not payload.get("email"):
        errors.append("email is required")
    if payload.get("age") is not None and payload["age"] < 0:
        errors.append("age must not be negative")
    return errors


def validate_member_payload(payload):
    errors = []
    if payload.get("age") is not None and payload["age"] < 0:
        errors.append("age must not be negative")
    if not payload.get("email"):
        errors.append("email is required")
    if not payload.get("name"):
        errors.append("name is required")
    return errors
