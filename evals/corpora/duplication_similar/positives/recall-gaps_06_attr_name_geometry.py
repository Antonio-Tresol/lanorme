# why: positive - two bounding-box computations identical in structure, only
# why: the attribute names on the point objects differ (x/y vs lon/lat). Numbers
# why: and ops match; DRY-001 misses it because attribute names stay in the dump.
"""Two extent calculators differing only by the coordinate attribute names."""

from __future__ import annotations


def screen_extent(points):
    min_a = min(p.x for p in points)
    max_a = max(p.x for p in points)
    min_b = min(p.y for p in points)
    max_b = max(p.y for p in points)
    return (min_a, min_b, max_a, max_b)


def geo_extent(points):
    min_a = min(p.lon for p in points)
    max_a = max(p.lon for p in points)
    min_b = min(p.lat for p in points)
    max_b = max(p.lat for p in points)
    return (min_a, min_b, max_a, max_b)
