"""Record a per-release evaluation audit as a single result JSON.

The audit captures the deterministic ACCURACY of every labelled-corpus scorer
(each ``evals/score_*.py`` exposing ``score()``) together with a hardware and
version METADATA stamp -- including the git commit and dirty flag that pin the
exact dataset and code that produced the numbers -- and, unless skipped, a
best-effort PERFORMANCE sweep that reuses the pinned end-to-end corpora. The
JSON is committed under ``evals/results/`` as the audit trail for a release.

Usage:
    uv run python evals/audit.py --version X.Y.Z [--no-perf] [--output PATH]

Flags:
    --version X.Y.Z   Release version being audited (required, non-empty).
    --no-perf         Skip the performance sweep (accuracy only).
    --output PATH     Write the JSON here instead of the default
                      evals/results/v<version>.json.

The run is non-interactive (no prompts). Progress and diagnostics go to stderr;
a concise one-line-per-rule summary goes to stdout.

Exit codes:
    0   success: every scorer produced metrics.
    1   a scorer reported a stale corpus or other error.
    2   usage error (missing or empty --version).
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from types import ModuleType
from typing import TypedDict

try:
    import lanorme
except Exception:  # noqa: BLE001 -- audit still records when the package is absent
    lanorme = None


class AccuracyRecord(TypedDict, total=False):
    """One scorer's outcome: either full metrics or an error note."""

    rule: str
    corpus: str
    tp: int
    fp: int
    fn: int
    tn: int
    precision: float
    recall: float
    f1: float
    error: str


class CorpusTiming(TypedDict, total=False):
    """One corpus' performance outcome: either a timing or a skip reason."""

    files: int
    lines: int
    seconds: float
    skipped: str


class Metadata(TypedDict):
    """Version and hardware stamp recorded with every audit."""

    audited_version: str
    lanorme_version: str
    git_commit: str
    git_dirty: bool
    python_version: str
    platform: str
    processor: str
    timestamp_utc: str


class Report(TypedDict):
    """The assembled audit document written to disk."""

    metadata: Metadata
    accuracy: list[AccuracyRecord]
    performance: dict[str, CorpusTiming]


_HERE = Path(__file__).resolve().parent
_REPO_ROOT = _HERE.parent
_RESULTS_DIR = _HERE / "results"
_PERF_RUNS = 3


def _discover_scorers() -> list[Path]:
    """Return the sorted list of ``evals/score_*.py`` module paths."""
    return sorted(_HERE.glob("score_*.py"))


def _import_module(*, path: Path) -> ModuleType:
    """Import a standalone benchmark module from its file path."""
    name = f"_audit_{path.stem}"
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _score_one(*, path: Path) -> AccuracyRecord:
    """Import one scorer and call ``score()``, mapping failures to a record.

    A stale corpus (``ValueError``) or any other failure becomes an entry with
    an ``error`` key and the scorer's ``RULE`` code when it can be read.
    """
    try:
        module = _import_module(path=path)
    except Exception as exc:  # noqa: BLE001 -- a broken module is recorded, not fatal
        return {"rule": path.stem, "error": f"import failed: {exc}"}

    rule = getattr(module, "RULE", path.stem)
    try:
        metrics: AccuracyRecord = module.score()
    except ValueError as exc:
        return {"rule": rule, "error": str(exc)}
    except Exception as exc:  # noqa: BLE001 -- record any scorer crash, never abort
        return {"rule": rule, "error": f"score() failed: {exc}"}
    return metrics


def _collect_accuracy(*, scorers: list[Path]) -> tuple[list[AccuracyRecord], bool]:
    """Score every scorer; return the records and whether any reported an error."""
    records: list[AccuracyRecord] = []
    failed = False
    for path in scorers:
        print(f"scoring {path.name} ...", file=sys.stderr)
        record = _score_one(path=path)
        if "error" in record:
            failed = True
            print(f"  error: {record['error']}", file=sys.stderr)
        records.append(record)
    return records, failed


def _collect_performance() -> dict[str, CorpusTiming]:
    """Time ``lanorme check`` over the pinned corpora, best-effort.

    Reuses ``run_benchmarks.py`` corpus preparation and timing. A corpus that
    cannot be downloaded (offline) is recorded as skipped rather than crashing
    the audit.
    """
    bench = _import_module(path=_REPO_ROOT / "benchmarks" / "run_benchmarks.py")
    corpora: dict[str, CorpusTiming] = {}
    for name, spec, _big in bench.CORPORA:
        print(f"timing {name} ...", file=sys.stderr)
        try:
            root = bench._ensure_corpus(name=name, spec=spec)
        except Exception as exc:  # noqa: BLE001 -- a download error must not abort
            corpora[name] = {"skipped": f"corpus error: {exc}"}
            continue
        if root is None:
            corpora[name] = {"skipped": "corpus unavailable (offline?)"}
            continue
        n_files, n_lines = bench._corpus_size(root=root)
        seconds = bench._time_end_to_end(root=root, runs=_PERF_RUNS)
        corpora[name] = {
            "files": n_files,
            "lines": n_lines,
            "seconds": round(seconds, 4),
        }
    return corpora


def _git_commit() -> str:
    """Return the short git commit hash, or 'unknown' if git is unavailable."""
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=_REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return "unknown"
    return out.stdout.strip() or "unknown"


def _git_dirty() -> bool:
    """Return True if the working tree has uncommitted changes.

    A dirty tree means the result was produced from code or corpora that no
    recorded commit captures, so ``git_commit`` alone would not reproduce it.
    """
    try:
        out = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=_REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return False
    return bool(out.stdout.strip())


def _lanorme_version() -> str:
    """Read ``__version__`` from the installed lanorme package."""
    if lanorme is None:
        return "unknown"
    return getattr(lanorme, "__version__", "unknown")


def _build_metadata(*, audited_version: str) -> Metadata:
    """Assemble the version and hardware stamp for the run."""
    return {
        "audited_version": audited_version,
        "lanorme_version": _lanorme_version(),
        "git_commit": _git_commit(),
        "git_dirty": _git_dirty(),
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "processor": platform.processor() or platform.machine(),
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    }


def _default_output(*, version: str) -> Path:
    """Return the canonical results path for a version."""
    return _RESULTS_DIR / f"v{version}.json"


def _write_report(*, report: Report, output: Path) -> None:
    """Write the report as indented JSON, creating the directory if needed."""
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")


def _print_summary(*, report: Report, output: Path, perf_enabled: bool) -> None:
    """Print a concise human summary to stdout, one line per rule."""
    for record in report["accuracy"]:
        rule = record.get("rule", "?")
        if "error" in record:
            print(f"{rule}: ERROR {record['error']}")
            continue
        print(
            f"{rule}: P={record['precision']:.3f} "
            f"R={record['recall']:.3f} F1={record['f1']:.3f}"
        )
    perf = report["performance"]
    if not perf_enabled:
        print("perf: skipped")
    else:
        timed = [n for n, d in perf.items() if "seconds" in d]
        skipped = [n for n, d in perf.items() if "skipped" in d]
        print(f"perf: timed {len(timed)}, skipped {len(skipped)}")
    print(f"written: {output}")


def _parse_args(*, argv: list[str]) -> argparse.Namespace:
    """Build the argument parser and parse ``argv``."""
    parser = argparse.ArgumentParser(
        prog="audit.py",
        description="Record a per-release benchmark audit JSON.",
        epilog=(
            "exit codes: 0 success; 1 a scorer reported a stale corpus or "
            "error; 2 usage error."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--version",
        dest="version",
        default="",
        help="Release version being audited (required, non-empty).",
    )
    parser.add_argument(
        "--no-perf",
        dest="no_perf",
        action="store_true",
        help="Skip the performance sweep (accuracy only).",
    )
    parser.add_argument(
        "--output",
        dest="output",
        default=None,
        help="Write the JSON here instead of evals/results/v<version>.json.",
    )
    return parser.parse_args(argv)


def _run(*, args: argparse.Namespace) -> int:
    """Execute the audit and return the process exit code."""
    version = args.version.strip()
    if not version:
        print("error: --version X.Y.Z is required and must be non-empty.", file=sys.stderr)
        return 2

    accuracy, failed = _collect_accuracy(scorers=_discover_scorers())
    perf_enabled = not args.no_perf
    performance = _collect_performance() if perf_enabled else {}

    report: Report = {
        "metadata": _build_metadata(audited_version=version),
        "accuracy": accuracy,
        "performance": performance,
    }
    output = Path(args.output) if args.output else _default_output(version=version)
    _write_report(report=report, output=output)
    _print_summary(report=report, output=output, perf_enabled=perf_enabled)
    return 1 if failed else 0


def main(*, argv: list[str]) -> int:
    """CLI entry point."""
    return _run(args=_parse_args(argv=argv))


if __name__ == "__main__":
    raise SystemExit(main(argv=sys.argv[1:]))
