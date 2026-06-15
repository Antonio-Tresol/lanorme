"""Disabled assignment and augmented-assignment statements."""

from __future__ import annotations


def compute_totals(items: list[dict]) -> dict:
    """Aggregate item totals."""
    total = 0
    # total = 0.0
    # subtotal = sum(it["price"] for it in items)
    # tax_rate = 0.075
    for it in items:
        total += it["price"]
        # total *= 1.075
    # discount = total * 0.1
    # total -= discount
    return {"total": total}


# DEFAULT_LIMIT = 50
# MAX_RETRIES = 3
# API_BASE = "https://api.example.com/v2"


class Counter:
    """Simple counter."""

    def __init__(self) -> None:
        self.value = 0
        # self.value = -1
        # self._lock = threading.Lock()
