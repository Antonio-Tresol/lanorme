# why: negative - two serialisers whose per-line attribute mappings ARE the content; each line maps a distinct field, so extracting a helper would just thread every difference through as a parameter with no real saving.
from __future__ import annotations


def user_to_dict(user):
    payload = {}
    payload["id"] = user.id
    payload["username"] = user.name
    payload["email"] = user.email_address
    payload["is_active"] = user.active
    payload["joined"] = user.created_at.isoformat()
    return payload


def order_to_dict(order):
    payload = {}
    payload["reference"] = order.ref
    payload["customer"] = order.buyer_id
    payload["total"] = order.amount_due
    payload["currency"] = order.currency_code
    payload["placed"] = order.placed_on.isoformat()
    payload["status"] = order.state
    return payload
