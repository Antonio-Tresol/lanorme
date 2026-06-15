# why: negative - two equality helpers that look parallel but use genuinely
# why: different structural shapes: one short-circuits with sequential guards,
# why: the other does a single tuple compare. The divergence survives name,
# why: string and number normalisation, so it is a real distinction not drift.
"""Two equality helpers with different control-flow shapes."""

from __future__ import annotations


def points_equal(self, other):
    if not isinstance(other, type(self)):
        return NotImplemented
    if self.x != other.x:
        return False
    if self.y != other.y:
        return False
    if self.z != other.z:
        return False
    return True


def ranges_equal(self, other):
    if not isinstance(other, type(self)):
        return NotImplemented
    mine = (self.lower, self.upper, self.inclusive)
    theirs = (other.lower, other.upper, other.inclusive)
    matched = mine == theirs
    return matched
