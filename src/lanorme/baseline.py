"""Warning baseline: record the findings a codebase already has so that only
new ones report.

On a brownfield codebase the advisory tier decays into wallpaper: the same
warnings ride every run, nobody acts on them, and a genuinely new warning
scrolls past unnoticed in the pile. A baseline records the existing debt and
holds the project to account only for what it adds. With ``extends = ["strict"]``
plus a baseline, every new line is held to strict from day one of a legacy repo.

The matching is content-anchored, never line-number-anchored, so an entry
survives unrelated edits above it. A finding is keyed by
``(file, rule code, anchor)`` where the anchor is a hash of the stripped source
line at the finding (or a hash of the finding message for file-level findings).
Hashing both forms keeps source text and any secret out of the committed file.

A baselined *warning* never suppresses a current *error*-tier finding, so a
baselined file that grows past a hard threshold re-reports and fails the build.
A per-key count budget guarantees that N recorded occurrences can never hide an
(N+1)th: new debt always surfaces.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

from lanorme import CheckResult, Status, Violation
from lanorme.filtering import _line_at, _rule_code

BASELINE_VERSION = 1

_ERROR = "error"
_WARNING = "warning"


# --------------------------------------------------------------------------- #
# Fingerprinting
# --------------------------------------------------------------------------- #


def _norm_path(file: str) -> str:
    """Normalise a finding path to forward slashes without a leading ``./``."""
    normalised = file.replace("\\", "/")
    return normalised[2:] if normalised.startswith("./") else normalised


def _anchor(
    *, project_root: Path, file: str, line: int, message: str, cache: dict[str, list[str]]
) -> str:
    """A stable, content-derived key for a finding.

    For a line-anchored finding the anchor is a hash of the stripped source
    line, so it survives unrelated edits above the finding. For a file-level
    finding (line <= 0) or a blank/unreadable line, it falls back to a hash of
    the raw message. Both forms are hashed, so neither source text nor any
    embedded secret reaches the committed baseline file.
    """
    if line >= 1:
        source = _line_at(project_root=project_root, file=file, line=line, cache=cache).strip()
        if source:
            return "sha:" + hashlib.sha256(source.encode("utf-8")).hexdigest()
    return "msg:" + hashlib.sha256(message.encode("utf-8")).hexdigest()


def _describe(rule: str) -> str:
    """The static rule description, with no per-finding (and so no secret) text.

    ``Violation.rule`` is a fixed string such as
    ``"SIZE-001: File approaching 500 effective lines"``; the dynamic detail
    lives in ``Violation.message``. Storing the description keeps the committed
    file readable for review without ever recording a value or a source snippet.
    """
    head, sep, tail = rule.partition(":")
    return tail.strip() if sep else head.strip()


def _finding_key(
    *, project_root: Path, finding: Violation, cache: dict[str, list[str]]
) -> tuple[str, str, str]:
    """The ``(path, code, anchor)`` identity used to match against the baseline."""
    return (
        _norm_path(finding.file),
        _rule_code(finding.rule),
        _anchor(
            project_root=project_root,
            file=finding.file,
            line=finding.line,
            message=finding.message,
            cache=cache,
        ),
    )


# --------------------------------------------------------------------------- #
# File I/O
# --------------------------------------------------------------------------- #


def _fail(message: str) -> None:
    """Print an error and exit 2 (the configuration/usage failure code)."""
    print(f"ERROR: {message}", file=sys.stderr)
    sys.exit(2)


def load_index(path: Path) -> dict[tuple[str, str, str], dict[str, object]]:
    """Read a baseline file into a key -> {severity, count} index, exiting cleanly
    on a missing or malformed file."""
    try:
        raw = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        _fail(f"baseline file '{path}' does not exist. Run 'lanorme baseline write' first.")
    except OSError as error:
        _fail(f"baseline file '{path}' could not be read: {error}")

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as error:
        _fail(f"baseline file '{path}' is not valid JSON: {error}")

    if not isinstance(data, dict) or data.get("version") != BASELINE_VERSION:
        _fail(f"baseline file '{path}' is not a version {BASELINE_VERSION} baseline.")
    entries = data.get("entries")
    if not isinstance(entries, list):
        _fail(f"baseline file '{path}' has no 'entries' list.")

    index: dict[tuple[str, str, str], dict[str, object]] = {}
    for entry in entries:
        key = (str(entry["file"]), str(entry["code"]), str(entry["anchor"]))
        slot = index.setdefault(key, {"severity": _WARNING, "count": 0})
        if entry.get("severity") == _ERROR:
            slot["severity"] = _ERROR
        slot["count"] = int(slot["count"]) + int(entry.get("count", 1))
    return index


def _serialise(entries: list[dict[str, object]]) -> str:
    """Render entries as deterministic, diff-friendly JSON with a trailing newline."""
    ordered = sorted(entries, key=lambda e: (e["file"], e["code"], e["anchor"]))
    payload = {"version": BASELINE_VERSION, "entries": ordered}
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


# --------------------------------------------------------------------------- #
# Building entries from a run
# --------------------------------------------------------------------------- #


def _accumulate(
    *,
    counts: dict[tuple[str, str, str], dict[str, object]],
    project_root: Path,
    finding: Violation,
    severity: str,
    cache: dict[str, list[str]],
) -> None:
    """Fold one finding into the per-key entry table, skipping crash notices."""
    # A finding with no file is a RUN-000 crash notice: transient and
    # version-dependent, so it is never recorded and never matched.
    if not finding.file:
        return
    key = _finding_key(project_root=project_root, finding=finding, cache=cache)
    slot = counts.get(key)
    if slot is None:
        counts[key] = {
            "file": key[0],
            "code": key[1],
            "anchor": key[2],
            "severity": severity,
            "message": _describe(finding.rule),
            "count": 1,
        }
        return
    slot["count"] = int(slot["count"]) + 1
    if severity == _ERROR:
        slot["severity"] = _ERROR


def _entries_from_results(
    *, results: list[CheckResult], project_root: Path
) -> list[dict[str, object]]:
    """Build the full entry list for the current findings of a clean run."""
    counts: dict[tuple[str, str, str], dict[str, object]] = {}
    cache: dict[str, list[str]] = {}
    for result in results:
        for violation in result.violations:
            _accumulate(
                counts=counts, project_root=project_root, finding=violation, severity=_ERROR, cache=cache
            )
        for warning in result.warnings:
            _accumulate(
                counts=counts, project_root=project_root, finding=warning, severity=_WARNING, cache=cache
            )
    return list(counts.values())


# --------------------------------------------------------------------------- #
# Suppression at check time
# --------------------------------------------------------------------------- #


def _is_suppressed(
    *,
    index: dict[tuple[str, str, str], dict[str, object]],
    consumed: dict[tuple[str, str, str], int],
    project_root: Path,
    finding: Violation,
    tier: str,
    cache: dict[str, list[str]],
) -> bool:
    """Decide whether one finding is covered by the baseline, honouring the
    severity gate and the per-key count budget."""
    if not finding.file:
        return False
    key = _finding_key(project_root=project_root, finding=finding, cache=cache)
    entry = index.get(key)
    if entry is None:
        return False
    # Severity gate: a recorded warning must never hide a current error-tier
    # finding (a baselined file that crossed a hard threshold must re-report).
    # The reverse is allowed: a recorded error suppresses its improved warning.
    if tier == _ERROR and entry["severity"] != _ERROR:
        return False
    used = consumed.get(key, 0)
    if used >= int(entry["count"]):
        return False
    consumed[key] = used + 1
    return True


def suppress(
    *, results: list[CheckResult], project_root: Path, baseline_path: Path
) -> list[CheckResult]:
    """Return results with baselined findings removed and statuses recomputed."""
    index = load_index(baseline_path)
    consumed: dict[tuple[str, str, str], int] = {}
    cache: dict[str, list[str]] = {}

    filtered: list[CheckResult] = []
    for result in results:
        violations = [
            v
            for v in result.violations
            if not _is_suppressed(
                index=index, consumed=consumed, project_root=project_root, finding=v, tier=_ERROR, cache=cache
            )
        ]
        warnings = [
            w
            for w in result.warnings
            if not _is_suppressed(
                index=index, consumed=consumed, project_root=project_root, finding=w, tier=_WARNING, cache=cache
            )
        ]
        status = Status.FAIL if violations else (Status.WARN if warnings else Status.PASS)
        filtered.append(
            CheckResult(check=result.check, status=status, violations=violations, warnings=warnings)
        )
    return filtered


# --------------------------------------------------------------------------- #
# Commands: write and status
# --------------------------------------------------------------------------- #


def write(*, results: list[CheckResult], project_root: Path, baseline_path: Path) -> None:
    """Record the current findings, printing a paydown summary (and, on the first
    write, the config block to adopt)."""
    first_write = not baseline_path.exists()
    old_keys = set() if first_write else set(load_index(baseline_path).keys())

    entries = _entries_from_results(results=results, project_root=project_root)
    new_keys = {(e["file"], e["code"], e["anchor"]) for e in entries}
    added = len(new_keys - old_keys)
    pruned = len(old_keys - new_keys)

    baseline_path.write_text(_serialise(entries), encoding="utf-8")

    total = sum(int(e["count"]) for e in entries)
    print(f"Wrote {len(entries)} baseline entries ({total} findings): +{added} new, -{pruned} pruned (was {len(old_keys)}).")
    if first_write:
        rel = baseline_path.name
        print(
            "\nAdd this to your configuration and commit the file like a lockfile:\n\n"
            "    [tool.lanorme]\n"
            f'    baseline = "{rel}"\n'
        )


def print_status(*, results: list[CheckResult], project_root: Path, baseline_path: Path) -> None:
    """List baseline entries that match nothing in the current run (stale debt)."""
    index = load_index(baseline_path)
    cache: dict[str, list[str]] = {}
    matched: set[tuple[str, str, str]] = set()
    for result in results:
        for finding in [*result.violations, *result.warnings]:
            if not finding.file:
                continue
            key = _finding_key(project_root=project_root, finding=finding, cache=cache)
            if key in index:
                matched.add(key)

    stale = sorted(key for key in index if key not in matched)
    if not stale:
        print(f"Baseline is current: all {len(index)} entries still match a finding.")
        return
    print(f"{len(stale)} stale baseline {'entry' if len(stale) == 1 else 'entries'} (matched nothing this run):")
    for file, code, _anchor_hash in stale:
        print(f"  {file}  {code}")
    print("\nRun 'lanorme baseline write' to prune them.")
