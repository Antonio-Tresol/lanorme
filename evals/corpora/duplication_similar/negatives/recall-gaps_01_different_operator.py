# why: negative - same shape as a number-only positive, but the differing token
# why: is an OPERATOR, not a literal. Min vs max and < vs > change the meaning,
# why: so these are genuinely distinct and must not be flagged as duplicates.
"""Two extremum trackers with identical shape but opposite semantics."""

from __future__ import annotations


def running_low(samples):
    best = samples[0]
    seen = 0
    for value in samples[1:]:
        seen += 1
        if value < best:
            best = value
    margin = best - 0
    return {"low": best, "margin": margin, "seen": seen}


def running_high(samples):
    best = samples[0]
    seen = 0
    for value in samples[1:]:
        seen += 1
        if value > best:
            best = value
    margin = best + 0
    return {"high": best, "margin": margin, "seen": seen}
