"""A larger contiguous disabled block left behind by a refactor."""

from __future__ import annotations


def export(rows: list[dict]) -> str:
    """Render rows as CSV."""
    # header = ",".join(rows[0].keys())
    # lines = [header]
    # for row in rows:
    #     line = ",".join(str(v) for v in row.values())
    #     lines.append(line)
    # return "\n".join(lines)
    import csv
    import io

    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=list(rows[0].keys()))
    writer.writeheader()
    writer.writerows(rows)
    return buf.getvalue()
