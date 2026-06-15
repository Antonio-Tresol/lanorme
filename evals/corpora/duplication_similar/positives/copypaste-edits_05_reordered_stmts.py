# why: positive - same computation with two independent setup statements reordered; semantically identical copy-paste, reviewer would extract a helper.
from __future__ import annotations


def render_summary(report, theme):
    width = theme.width
    palette = theme.palette
    lines = []
    lines.append(report.title.upper())
    lines.append("=" * width)
    for section in report.sections:
        lines.append(section.format(palette))
    return "\n".join(lines)


def render_digest(report, theme):
    palette = theme.palette
    width = theme.width
    lines = []
    lines.append(report.title.upper())
    lines.append("=" * width)
    for section in report.sections:
        lines.append(section.format(palette))
    return "\n".join(lines)
