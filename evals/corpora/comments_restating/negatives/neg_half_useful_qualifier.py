"""Half-useful-qualifier negatives.

Surface form is the same as the positive twin (paraphrase plus one qualifier),
but here the qualifier carries genuine new information — a contract, an
external constraint, a unit, or an upstream guarantee — that is NOT
recoverable from the adjacent code. These should NOT be flagged.
"""

from __future__ import annotations


def process_csv(rows: list[str]) -> list[str]:
    # loop over rows in reverse because the consumer expects newest-first
    for row in reversed(rows):
        print(row)
    return rows


def trimmed(values: list[int]) -> list[int]:
    # drop the first and last element; upstream pads with sentinels we must discard
    return values[1:-1]


def lookup(data: dict[str, int], key: str) -> int:
    # return the value for key; 0 is the documented "absent" sentinel in the API
    return data.get(key, 0)


def cap_payload(payload: bytes) -> bytes:
    # truncate to fit the kernel's UDP MTU of 1024 on this platform
    return payload[:1024]


def merge_unique(a: list[int], b: list[int]) -> list[int]:
    # union of a and b; order is intentionally unspecified per the public contract
    return list(set(a) | set(b))


def trimmed_lowercased(name: str) -> str:
    # normalize for case-insensitive equality per RFC 4518 section 2.2
    return name.strip().lower()
