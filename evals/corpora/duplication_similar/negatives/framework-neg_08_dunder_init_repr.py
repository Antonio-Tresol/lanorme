# why: negative - __init__ assigns fields and __repr__ formats them; they walk the same attribute list but one stores and one renders, so the bodies are structurally different and not mergeable.
from __future__ import annotations


class Customer:
    def __init__(self, customer_id, name, email, tier, balance):
        self.customer_id = customer_id
        self.name = name
        self.email = email
        self.tier = tier
        self.balance = balance
        self._dirty = False

    def __repr__(self):
        parts = []
        parts.append(f"id={self.customer_id!r}")
        parts.append(f"name={self.name!r}")
        parts.append(f"tier={self.tier!r}")
        parts.append(f"balance={self.balance:.2f}")
        body = ", ".join(parts)
        return f"Customer({body})"
