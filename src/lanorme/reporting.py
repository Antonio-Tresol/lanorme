"""Output rendering for the LaNorme CLI.

Everything that turns check results into text lives here: the four ``check``
output formats (``concise``, ``full``, ``json``, ``ndjson``), the ``rules``
listing, the ``rule CODE`` reference lookup, and the ``--show-config`` dump.
Keeping rendering separate from orchestration keeps ``cli.py`` focused on
parsing arguments and running checks.
"""

from __future__ import annotations

import dataclasses
import json
import os
import sys
from importlib.resources import files as _resource_files
from pathlib import Path

from lanorme import CheckResult, Status, get_all_checks


# --------------------------------------------------------------------------- #
# Check results
# --------------------------------------------------------------------------- #


def _finding_records(*, result: CheckResult) -> list[dict[str, str | int]]:
    """Flatten a check result into one record per finding (violations + warnings)."""
    records: list[dict[str, str | int]] = []
    for severity, items in (("error", result.violations), ("warning", result.warnings)):
        for finding in items:
            records.append({"check": result.check, "severity": severity, **finding.to_dict()})
    return records


def _emit_ndjson(*, results: list[CheckResult]) -> None:
    """Print one JSON object per finding, newline-delimited (grep/jq friendly)."""
    for result in results:
        for record in _finding_records(result=result):
            print(json.dumps(record))


def _emit_human(*, results: list[CheckResult], show_passed: bool) -> None:
    """Print the human report.

    ``full`` (*show_passed* true) reproduces the verbose per-check listing exactly,
    with no summary footer. ``concise`` (*show_passed* false) prints only the checks
    that found something, then a one-line summary so an empty run is not silent.
    """
    shown = 0
    for result in results:
        if not show_passed and result.status == Status.PASS:
            continue
        print(result.format_human())
        print()
        shown += 1

    if show_passed:
        return

    passed = sum(1 for r in results if r.status == Status.PASS)
    warned = sum(1 for r in results if r.status == Status.WARN)
    failed = sum(1 for r in results if r.status == Status.FAIL)
    if shown == 0:
        print(f"All {len(results)} checks passed.")
    else:
        print(f"Summary: {len(results)} checks — {passed} passed, {warned} warnings, {failed} failed.")


def _gh_escape(text: str) -> str:
    """Escape annotation message data per the GitHub workflow-command spec."""
    return text.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")


def _emit_github(*, results: list[CheckResult]) -> None:
    """Emit GitHub Actions workflow commands so findings appear inline on PR diffs.

    The ``title`` uses the rule *code* (``DRY-001``), not the full rule string:
    annotation properties are comma-separated and terminated by ``::``, so a
    title carrying the rule's ``: `` description or a comma would corrupt the
    annotation. The message keeps its full text with newlines encoded as ``%0A``.
    """
    for result in results:
        for v in result.violations:
            print(f"::error file={v.file},line={v.line},title={v.code}::{_gh_escape(v.message)}")
        for w in result.warnings:
            print(f"::warning file={w.file},line={w.line},title={w.code}::{_gh_escape(w.message)}")


def resolve_output_format(*, explicit: str | None, as_json: bool) -> str:
    """Pick the output format: ``--json`` wins, then an explicit ``--output-format``.

    Only an unset format auto-detects, choosing ``github`` inside GitHub Actions
    (so findings annotate the PR diff) and ``concise`` otherwise. An explicit
    choice is always honoured, even in CI.
    """
    if as_json:
        return "json"
    if explicit is not None:
        return explicit
    if os.environ.get("GITHUB_ACTIONS") == "true":
        return "github"
    return "concise"


def emit(*, results: list[CheckResult], output_format: str) -> None:
    """Dispatch results to the requested output format."""
    if output_format == "json":
        print(json.dumps([r.to_dict() for r in results], indent=2))
    elif output_format == "ndjson":
        _emit_ndjson(results=results)
    elif output_format == "github":
        _emit_github(results=results)
    else:
        _emit_human(results=results, show_passed=output_format == "full")


# --------------------------------------------------------------------------- #
# Rules listing
# --------------------------------------------------------------------------- #


def print_rules() -> None:
    """Print every registered check and its rules."""
    checks = get_all_checks()
    if not checks:
        print("No checks registered.")
        return
    for check in sorted(checks.values(), key=lambda c: c.name):
        print(f"\n## {check.name} — {check.description}")
        for rule in check.rules:
            print(f"  {rule}")


# --------------------------------------------------------------------------- #
# Single-rule reference (docs/RULES.md)
# --------------------------------------------------------------------------- #


def _rules_reference_path() -> Path | None:
    """Locate the rule reference Markdown, preferring the package-bundled copy."""
    bundled = _resource_files("lanorme").joinpath("RULES.md")
    if bundled.is_file():
        return Path(str(bundled))
    for candidate in (
        Path(__file__).resolve().parents[2] / "docs" / "RULES.md",
        Path.cwd() / "docs" / "RULES.md",
    ):
        if candidate.is_file():
            return candidate
    return None


def _rule_reference_section(*, code: str) -> str | None:
    """Return the ``docs/RULES.md`` section that documents *code*, or None.

    Matches by looking for a Markdown header whose backtick-quoted token
    starts with the code (e.g. ``### `CMT-001`: ...``) or a category
    header (e.g. ``## Comments: `CMT-*` ...``) where the code's category
    appears in a backtick token. The section is everything up to the next
    same-or-shallower header.
    """
    reference = _rules_reference_path()
    if reference is None:
        return None
    text = reference.read_text(encoding="utf-8")
    code_token = f"`{code}`"
    category = code.split("-", 1)[0]
    category_token = f"`{category}-"
    lines = text.splitlines()
    exact = [i for i, line in enumerate(lines) if line.startswith("#") and code_token in line]
    category_only = [
        i for i, line in enumerate(lines) if line.startswith("#") and category_token in line
    ]
    if not exact and not category_only:
        return None
    start = exact[0] if exact else category_only[0]
    header_level = len(lines[start]) - len(lines[start].lstrip("#"))
    end = len(lines)
    for index in range(start + 1, len(lines)):
        if lines[index].startswith("#"):
            level = len(lines[index]) - len(lines[index].lstrip("#"))
            if level <= header_level:
                end = index
                break
    return "\n".join(lines[start:end]).rstrip() + "\n"


def print_rule_detail(*, code: str) -> int:
    """Print the reference section for *code* and return an exit code."""
    section = _rule_reference_section(code=code.upper())
    if section is not None:
        print(section)
        return 0
    print(
        f"No reference section found for {code!r}. Run 'lanorme rules' for the list "
        "of emitted codes, or browse docs/RULES.md directly.",
        file=sys.stderr,
    )
    return 2


# --------------------------------------------------------------------------- #
# Effective configuration (--show-config)
# --------------------------------------------------------------------------- #


def _settings_repr(check: object) -> str:
    """One-line summary of a check's effective settings after configuration."""
    if not dataclasses.is_dataclass(check):
        return ""
    parts: list[str] = []
    if hasattr(check, "enabled"):
        parts.append(f"enabled={check.enabled}")
    for field in dataclasses.fields(check):
        if field.name in {"name", "description", "rules", "enabled"}:
            continue
        value = getattr(check, field.name)
        text = repr(value)
        if len(text) > 48:
            if isinstance(value, (list, tuple, set, frozenset)):
                text = f"<{len(value)} items>"
            elif isinstance(value, dict):
                text = f"<{len(value)} keys>"
            else:
                text = text[:45] + "..."
        parts.append(f"{field.name}={text}")
    summary = " ".join(parts)
    if hasattr(check, "enabled") and not check.enabled:
        summary += "   (opt-in, not enabled)"
    return summary


def print_config(*, config: dict[str, object], source: str | None, project_root: Path) -> None:
    """Print the discovered config file and the effective settings for every check."""
    print(f"config file:  {source or 'none (built-in defaults)'}")
    print(f"project root: {project_root}")
    top = [k for k in ("select", "ignore", "exclude", "source_root", "plugins") if k in config]
    if top or config.get("per-file-ignores"):
        print("\n[tool.lanorme]")
        for key in top:
            print(f"  {key} = {config[key]!r}")
        if config.get("per-file-ignores"):
            print(f"  per-file-ignores = {config['per-file-ignores']!r}")
    print("\nchecks (effective settings):")
    for name, check in sorted(get_all_checks().items()):
        print(f"  {name:<18} {_settings_repr(check)}")
