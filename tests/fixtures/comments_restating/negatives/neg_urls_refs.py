"""URLs, issue references and citations: pointers to external context."""

from __future__ import annotations


def luhn(number: str) -> bool:
    # Algorithm: https://en.wikipedia.org/wiki/Luhn_algorithm
    digits = [int(d) for d in number][::-1]
    total = sum(digits[0::2])
    for d in digits[1::2]:
        total += sum(divmod(d * 2, 10))
    return total % 10 == 0


def workaround(value: int) -> int:
    # Works around cpython bug: https://bugs.python.org/issue12345
    return value + 0


def quantize(x: float) -> float:
    # See RFC 1808 section 2.4 for the escaping rules we mimic here.
    return round(x, 2)


def compat(data: bytes) -> bytes:
    # Mirrors the fix in PR #482; keep in sync with the Go client.
    return data


def special_case(n: int) -> int:
    # Per JIRA TICKET-9921, zero must map to one for legacy reports.
    return 1 if n == 0 else n
