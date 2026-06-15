# why: positive - realistic drift combining two misses: a different attribute
# why: name and a different numeric threshold. Each alone defeats DRY-001, and
# why: together they still describe one helper a reviewer would extract.
"""Two threshold checks differing by an attribute name and a numeric limit."""

from __future__ import annotations


def cpu_is_overloaded(sample):
    usage = sample.cpu_percent
    smoothed = usage * 0.8 + sample.previous * 0.2
    over = smoothed > 90
    note = "cpu high" if over else "cpu ok"
    return {"over": over, "value": smoothed, "note": note}


def mem_is_overloaded(sample):
    usage = sample.mem_percent
    smoothed = usage * 0.8 + sample.previous * 0.2
    over = smoothed > 75
    note = "cpu high" if over else "cpu ok"
    return {"over": over, "value": smoothed, "note": note}
