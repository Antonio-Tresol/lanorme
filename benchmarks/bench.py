"""Execution-time benchmark for LaNorme on a Python codebase.

Usage:
    uv run python benchmarks/bench.py <path> [runs]

LaNorme runs every check independently (each walks and parses the tree itself),
so the realistic full-suite cost is the *sum* of the per-check times. This
benchmark also measures a single walk+parse pass, so the ratio shows how much a
shared/centralized parse cache could theoretically save, the evidence for
whether shared processing is worth the loss of check independence.
"""

from __future__ import annotations

import ast
import platform
import statistics
import sys
import time
from pathlib import Path

from lanorme import Check, get_all_checks
from lanorme.cli import _load_builtin_checks


def _corpus_stats(*, root: Path) -> tuple[int, int]:
    """Return (file count, total line count) for *.py under root."""
    files = list(root.rglob("*.py"))
    lines = 0
    for path in files:
        try:
            lines += len(path.read_text(encoding="utf-8").splitlines())
        except OSError:
            continue
    return len(files), lines


def _parse_pass(*, root: Path) -> float:
    """Time a single walk + read + ast.parse over the whole tree."""
    start = time.perf_counter()
    for path in root.rglob("*.py"):
        try:
            ast.parse(path.read_text(encoding="utf-8"))
        except (OSError, SyntaxError):
            continue
    return time.perf_counter() - start


def _time_check(*, check: Check, root: str, runs: int) -> float:
    """Return the median wall-clock time of running one check."""
    samples: list[float] = []
    for _ in range(runs):
        start = time.perf_counter()
        check.run(src_root=root)
        samples.append(time.perf_counter() - start)
    return statistics.median(samples)


def main(argv: list[str]) -> None:
    if not argv:
        print("usage: bench.py <path> [runs]")
        raise SystemExit(2)

    root = Path(argv[0])
    runs = int(argv[1]) if len(argv) > 1 else 3

    _load_builtin_checks()
    checks = get_all_checks()

    n_files, n_lines = _corpus_stats(root=root)
    parse = _parse_pass(root=root)

    # Warm the filesystem cache before timing.
    for check in checks.values():
        check.run(src_root=str(root))

    rows = sorted(
        ((name, _time_check(check=check, root=str(root), runs=runs)) for name, check in checks.items()),
        key=lambda row: row[1],
        reverse=True,
    )
    total = sum(t for _, t in rows)

    print(
        f"LaNorme benchmark — Python {platform.python_version()} "
        f"on {platform.system()} {platform.machine()}"
    )
    print(f"corpus: {root}  ({n_files} .py files, {n_lines:,} lines)  runs={runs} (median)")
    print(f"single walk+parse pass: {parse * 1000:.1f} ms\n")
    print(f"{'check':22}{'median':>10}{'×1 parse':>10}")
    print("-" * 42)
    for name, seconds in rows:
        ratio = seconds / parse if parse else 0.0
        print(f"{name:22}{seconds * 1000:>8.1f}ms{ratio:>9.1f}x")
    print("-" * 42)
    total_no_meta = sum(seconds for name, seconds in rows if name != "meta")
    parsing_checks = sum(1 for name, seconds in rows if name != "meta" and seconds > parse)
    print(f"{'TOTAL (independent)':22}{total * 1000:>8.1f}ms")
    print(f"{'  excluding meta':22}{total_no_meta * 1000:>8.1f}ms  (meta re-runs every check)")
    if parse and total_no_meta:
        redundant = max(parsing_checks - 1, 0) * parse
        print(
            f"\n~{parsing_checks} checks each parse the tree independently. A shared parse "
            f"cache could save ≈ {redundant * 1000:.0f} ms "
            f"({redundant / total_no_meta * 100:.0f}% of the non-meta cost) — "
            f"the cost/benefit of giving up check independence."
        )


if __name__ == "__main__":
    main(sys.argv[1:])
