# why: positive - two validators that are the same trim-check-bounds routine copy-pasted with a different error message and one attribute swap (.title vs .body); a shared helper would remove the duplicated body.
from __future__ import annotations


def validate_heading(record):
    cleaned = record.title.strip()
    if not cleaned:
        raise ValueError("heading is required")
    if len(cleaned) > 80:
        raise ValueError("heading too long")
    record.title = cleaned
    return cleaned


def validate_caption(record):
    cleaned = record.body.strip()
    if not cleaned:
        raise ValueError("caption must be set")
    if len(cleaned) > 80:
        raise ValueError("caption exceeds limit")
    record.body = cleaned
    return cleaned
