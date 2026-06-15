# why: negative - two pydantic field validators share the validator scaffold but enforce unrelated rules (length plus character classes vs strip/lower plus reserved-word check); each branch encodes a distinct policy.
from __future__ import annotations

from pydantic import field_validator


class Account:
    @field_validator("password")
    @classmethod
    def validate_password(cls, value):
        if len(value) < 12:
            raise ValueError("password too short")
        if not any(c.isdigit() for c in value):
            raise ValueError("password needs a digit")
        if not any(c.isupper() for c in value):
            raise ValueError("password needs an upper-case letter")
        if value.lower() == value:
            raise ValueError("password needs mixed case")
        return value

    @field_validator("username")
    @classmethod
    def validate_username(cls, value):
        cleaned = value.strip().lower()
        if not cleaned:
            raise ValueError("username is required")
        if cleaned in {"admin", "root", "system"}:
            raise ValueError("username is reserved")
        if not cleaned.isalnum():
            raise ValueError("username must be alphanumeric")
        return cleaned
