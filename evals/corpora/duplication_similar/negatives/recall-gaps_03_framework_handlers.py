# why: negative - two route handlers that share framework scaffolding but have
# why: genuinely different control flow: the order path has an extra branch and
# why: builds its payload by iterating line items, while the user path is flat.
# why: The shape difference survives name and literal normalisation.
"""Two route handlers with divergent control flow, not extractable clones."""

from __future__ import annotations


def get_user(user_id, repo):
    record = repo.users.find(user_id)
    if record is None:
        raise LookupError("user not found")
    record.touch_access()
    payload = {"id": record.id, "name": record.name, "role": record.role}
    return payload


def get_order(order_id, repo):
    record = repo.orders.find(order_id)
    if record is None:
        raise LookupError("order not found")
    if record.is_archived:
        raise PermissionError("order is archived")
    lines = []
    for line in record.lines:
        lines.append({"sku": line.sku, "qty": line.qty})
    payload = {"id": record.id, "total": record.total, "lines": lines}
    return payload
