"""Colon-bearing comments that look dict/annotation-shaped but are prose."""

from __future__ import annotations


def render(payload: dict) -> str:
    # key: value pairs are flattened into a single line
    # status: one of {pending, active, retired}
    # owner: defaults to the requesting user when omitted
    # priority: integer between 0 and 9 (higher means more urgent)
    return ",".join(f"{k}={v}" for k, v in payload.items())


def authenticate(req: dict) -> bool:
    # input: HTTP request mapping with an Authorization header
    # output: True iff the bearer token validates against the keystore
    # side effects: refreshes the in-memory keystore cache when stale
    return "Authorization" in req


# environment: production
# region: us-east-1
# tier: premium
