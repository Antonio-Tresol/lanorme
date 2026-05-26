"""Genuine restatements phrased in natural English (synonyms of the code).

Each comment says exactly what the next line does, but using ordinary words
instead of the literal identifiers, so a substring detector cannot see it.
These are still redundant comments that should be flagged.
"""

from __future__ import annotations


def tally(counter: int, items: list[int], names: list[str]) -> int:
    # increment the counter
    counter += 1

    # loop over the items
    for item in items:
        print(item)

    # sort the names
    names.sort()

    return counter


def make(values: list[int]) -> dict[str, int]:
    # create an empty dictionary
    output = {}

    # add each value to the dictionary
    for index, value in enumerate(values):
        output[str(index)] = value

    # give back the dictionary
    return output


def toggle(flag: bool) -> bool:
    # flip the flag
    flag = not flag
    return flag


def grow(buffer: list[int], amount: int) -> None:
    # double the amount
    amount = amount * 2
    buffer.append(amount)
