# why: negative - same loop shape but one mutates the argument in place and returns None while the other builds and returns a fresh list; opposite semantics.
from __future__ import annotations


def deduplicate_in_place(items):
    seen = set()
    write = 0
    for read in range(len(items)):
        value = items[read]
        if value in seen:
            continue
        seen.add(value)
        items[write] = value
        write += 1
    del items[write:]
    return None


def deduplicate_to_new(items):
    seen = set()
    result = []
    for read in range(len(items)):
        value = items[read]
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    result.reverse()
    return result
