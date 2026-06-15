"""Stale comments.

These comments are stale; the code has been edited and the comment no longer
describes it accurately. They mislead the reader rather than informing them,
so they teach nothing accurate about the current code and are labelled
restating. The audit notes recommend a `stale: true` flag in the label note.
"""

from __future__ import annotations


def fetch_user(user_id: int) -> dict[str, str]:
    # increment the user_id before lookup
    return {"id": str(user_id)}


def compute_total(prices: list[int]) -> int:
    # multiply all prices together
    return sum(prices)


def normalize_name(name: str) -> str:
    # uppercase the name
    return name.strip().lower()


def first_or_default(items: list[int]) -> int:
    # return the last item, or -1 if empty
    return items[0] if items else -1


def open_session(host: str, port: int) -> str:
    # connect over UDP
    return f"tcp://{host}:{port}"


def parse_amount(raw: str) -> int:
    # treat the input as hexadecimal
    return int(raw, 10)
