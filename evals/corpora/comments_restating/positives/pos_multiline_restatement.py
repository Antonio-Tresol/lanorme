"""Multi-line restatements.

A single comment paraphrases the multi-line code block immediately below it.
The summary is just a re-narration of the steps the code already performs.
Should be flagged as restating.
"""

from __future__ import annotations


def squared_sum(values: list[int]) -> int:
    # square each value, then sum the squares
    squares = [v * v for v in values]
    return sum(squares)


def open_and_read(path: str) -> str:
    # open the file, read its contents, then close it
    handle = open(path, "r")
    data = handle.read()
    handle.close()
    return data


def lower_and_strip(items: list[str]) -> list[str]:
    # lowercase each item and strip whitespace
    out = []
    for item in items:
        out.append(item.strip().lower())
    return out


def double_then_filter(values: list[int], threshold: int) -> list[int]:
    # double each value, then keep only the ones above the threshold
    doubled = [v * 2 for v in values]
    return [v for v in doubled if v > threshold]


def merge_dicts(a: dict[str, int], b: dict[str, int]) -> dict[str, int]:
    # copy a, then update with b
    out = dict(a)
    out.update(b)
    return out
