"""Half-useful-qualifier restatements.

Each comment paraphrases the *what* and tacks on a qualifier clause that
*looks* extra-informative ("to skip the header", "to ignore the trailer",
"to drop the prefix", etc.) but the qualifier is itself encoded by a slice
literal, a default argument, or a chained call in the adjacent code. A
competent reviewer would read the qualifier directly off the code, so the
comment teaches nothing new and should be flagged as restating.
"""

from __future__ import annotations


def process_csv(rows: list[str]) -> list[str]:
    # loop over rows in reverse to skip the header
    for row in reversed(rows[1:]):
        print(row)
    return rows


def trimmed(values: list[int]) -> list[int]:
    # drop the first and last element to keep just the interior slice
    return values[1:-1]


def lookup(data: dict[str, int], key: str) -> int:
    # return the value for key, falling back to zero when the key is missing
    return data.get(key, 0)


def cap_payload(payload: bytes) -> bytes:
    # take the prefix of the payload to fit the first 1024 bytes
    return payload[:1024]


def merge_unique(a: list[int], b: list[int]) -> list[int]:
    # combine a and b into a list, removing duplicates via a set
    return list(set(a) | set(b))


def trimmed_lowercased(name: str) -> str:
    # lowercase the name after stripping the surrounding whitespace
    return name.strip().lower()
