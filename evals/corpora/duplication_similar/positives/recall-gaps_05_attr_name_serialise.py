# why: positive - two serialisers reading the same shaped object; only the
# why: attribute names accessed differ. DRY-001 leaves attribute names in the
# why: dump so it misses this; the fix is one helper over a shared protocol.
"""Two serialisers differing only by which attribute names they read."""

from __future__ import annotations


def serialise_customer(entity):
    payload = {}
    payload["id"] = entity.customer_id
    payload["label"] = entity.display_name
    payload["created"] = entity.created_at.isoformat()
    payload["active"] = bool(entity.is_enabled)
    return payload


def serialise_vendor(entity):
    payload = {}
    payload["id"] = entity.vendor_id
    payload["label"] = entity.trading_name
    payload["created"] = entity.opened_at.isoformat()
    payload["active"] = bool(entity.is_live)
    return payload
