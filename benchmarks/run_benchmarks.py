"""Reproducible end-to-end benchmark for LaNorme over canonical Python corpora.

Measures the wall-clock time of a real ``lanorme check <path>`` invocation
(full process: import, discovery, every check including meta), i.e. what a
user actually feels, across a fixed, version-pinned set of real-world
codebases, so numbers are comparable across machines and over time.

    uv run python benchmarks/run_benchmarks.py            # all corpora
    uv run python benchmarks/run_benchmarks.py --quick    # skip the big ones
    uv run python benchmarks/run_benchmarks.py --runs 5

Corpora are downloaded once (pinned sdists from PyPI) into benchmarks/.corpora/
and cached. The standard library is used in place. Network is only needed the
first time, and only for the PyPI corpora.
"""

from __future__ import annotations

import argparse
import io
import json
import statistics
import subprocess
import sys
import sysconfig
import tarfile
import time
import urllib.request
from pathlib import Path

# Version-pinned canonical corpora. (name, spec, big?), spec is "stdlib" or
# "<pkg>==<version>". Pins are deliberately old so they stay reproducible.
CORPORA: list[tuple[str, str, bool]] = [
    ("requests", "requests==2.31.0", False),
    ("flask", "flask==3.0.0", False),
    ("rich", "rich==13.7.0", False),
    ("sqlalchemy", "sqlalchemy==2.0.23", True),
    ("stdlib", "stdlib", True),
]

_CACHE = Path(__file__).parent / ".corpora"


def _sdist_url(*, pkg: str, version: str) -> str:
    api = f"https://pypi.org/pypi/{pkg}/{version}/json"
    with urllib.request.urlopen(api, timeout=30) as response:  # noqa: S310 (trusted host)
        data = json.load(response)
    for entry in data["urls"]:
        if entry["packagetype"] == "sdist":
            return entry["url"]
    raise RuntimeError(f"no sdist for {pkg}=={version}")


def _ensure_corpus(*, name: str, spec: str) -> Path | None:
    if spec == "stdlib":
        return Path(sysconfig.get_paths()["stdlib"])

    dest = _CACHE / name
    if dest.is_dir():
        return dest

    pkg, version = spec.split("==")
    try:
        url = _sdist_url(pkg=pkg, version=version)
        with urllib.request.urlopen(url, timeout=120) as response:  # noqa: S310
            payload = response.read()
    except OSError as exc:
        print(f"  ! skipping {name}: download failed ({exc})")
        return None

    dest.mkdir(parents=True, exist_ok=True)
    with tarfile.open(fileobj=io.BytesIO(payload), mode="r:gz") as tar:
        tar.extractall(dest, filter="data")
    return dest


def _corpus_size(*, root: Path) -> tuple[int, int]:
    files = list(root.rglob("*.py"))
    lines = 0
    for path in files:
        try:
            lines += len(path.read_text(encoding="utf-8").splitlines())
        except (OSError, UnicodeDecodeError):
            continue
    return len(files), lines


def _time_end_to_end(*, root: Path, runs: int) -> float:
    """Median wall-clock of a real `python -m lanorme check <root>` process."""
    cmd = [sys.executable, "-m", "lanorme", "check", str(root), "--output-format", "json"]
    samples: list[float] = []
    for _ in range(runs):
        start = time.perf_counter()
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
        samples.append(time.perf_counter() - start)
    return statistics.median(samples)


def main(argv: list[str]) -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--quick", action="store_true", help="Skip the large corpora.")
    parser.add_argument("--runs", type=int, default=3, help="Timed runs per corpus (median).")
    args = parser.parse_args(argv)

    print(f"LaNorme end-to-end benchmark — Python {sys.version.split()[0]}  runs={args.runs}\n")
    print(f"{'corpus':14}{'files':>8}{'lines':>12}{'end-to-end':>14}{'k lines/s':>12}")
    print("-" * 60)

    for name, spec, big in CORPORA:
        if big and args.quick:
            continue
        root = _ensure_corpus(name=name, spec=spec)
        if root is None:
            continue
        n_files, n_lines = _corpus_size(root=root)
        seconds = _time_end_to_end(root=root, runs=args.runs)
        klps = (n_lines / 1000) / seconds if seconds else 0.0
        print(f"{name:14}{n_files:>8}{n_lines:>12,}{seconds * 1000:>11.0f} ms{klps:>11.1f}", flush=True)

    print("-" * 60)
    print("end-to-end = full `lanorme check` process incl. meta; see bench.py for per-check.")


if __name__ == "__main__":
    main(sys.argv[1:])
