"""Post-run filtering of check results: rule-code matching, ``# noqa``, promotion.

These helpers operate purely on the ``CheckResult`` list a run produces. They
carry no argument-parsing or config-discovery concern, so they live apart from
``cli.py`` (which orchestrates them). Each ``_apply_*`` returns a new list with
statuses recomputed; none mutates its input.
"""

from __future__ import annotations

import re
from pathlib import Path

from lanorme import CheckResult, Status, Violation

_CODE_RE = re.compile(r"^([A-Z]+)-\d+")


def _rule_code(rule: str) -> str:
    """Extract the rule code (e.g. 'LAYER-002') from a rule string."""
    return rule.split(":", 1)[0].strip().split()[0]


def _category(code: str) -> str:
    """The category prefix of a code, e.g. 'LAYER' from 'LAYER-002'."""
    match = _CODE_RE.match(code)
    return match.group(1) if match else code


def _matches(*, code: str, patterns: list[str]) -> bool:
    """True if *code* matches any selector (exact code, category, or 'ALL').

    Case-insensitive, and whitespace and empty entries are ignored, so a
    selector from a config list (``[" type-004 "]``) behaves like the CLI form
    (``--promote 'type-004'``), which is normalised by ``_csv``.
    """
    code_upper = code.upper()
    category = _category(code_upper)
    wanted = {p.strip().upper() for p in patterns if p.strip()}
    return any(p in ("ALL", code_upper, category) for p in wanted)


def _keep(*, rule: str, select: list[str], ignore: list[str]) -> bool:
    code = _rule_code(rule)
    selected = not select or _matches(code=code, patterns=select)
    return selected and not _matches(code=code, patterns=ignore)


# --------------------------------------------------------------------------- #
# ``# noqa`` suppression
# --------------------------------------------------------------------------- #

_NOQA_RE = re.compile(r"#\s*noqa(?:\s*:\s*([A-Za-z0-9_,\-\s]+))?", re.IGNORECASE)


def _noqa_silences(*, line: str, rule: str) -> bool:
    """True if *line* carries a ``# noqa`` comment that covers *rule*."""
    match = _NOQA_RE.search(line)
    if match is None:
        return False
    if match.group(1) is None:
        return True  # bare `# noqa` silences any rule on this line
    codes = [c.strip() for c in match.group(1).split(",") if c.strip()]
    code = _rule_code(rule)
    return _matches(code=code, patterns=codes)


def _line_at(*, project_root: Path, file: str, line: int, cache: dict[str, list[str]]) -> str:
    """Read source line *line* from *file*, caching the file's lines for the run."""
    key = file.replace("\\", "/")
    lines = cache.get(key)
    if lines is None:
        path = project_root / file
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeDecodeError):
            lines = []
        cache[key] = lines
    if not lines or line <= 0 or line > len(lines):
        return ""
    return lines[line - 1]


def _apply_noqa(*, results: list[CheckResult], project_root: Path) -> list[CheckResult]:
    """Drop violations/warnings whose source line carries a covering ``# noqa`` comment."""
    cache: dict[str, list[str]] = {}

    def should_keep(violation: Violation) -> bool:
        line = _line_at(
            project_root=project_root, file=violation.file, line=violation.line, cache=cache
        )
        return not _noqa_silences(line=line, rule=violation.rule)

    filtered: list[CheckResult] = []
    for result in results:
        violations = [v for v in result.violations if should_keep(v)]
        warnings = [w for w in result.warnings if should_keep(w)]
        status = Status.FAIL if violations else (Status.WARN if warnings else Status.PASS)
        filtered.append(
            CheckResult(
                check=result.check,
                status=status,
                violations=violations,
                warnings=warnings,
            )
        )
    return filtered


# --------------------------------------------------------------------------- #
# Severity promotion
# --------------------------------------------------------------------------- #


def _apply_promotions(*, results: list[CheckResult], promote: list[str]) -> list[CheckResult]:
    """Promote advisory warnings whose code matches *promote* into violations.

    Lets a project escalate heuristic, default-warning rules (for example
    ``TYPE-004`` or ``SIMILAR-001``) into build-failing errors via
    ``[tool.lanorme] promote`` or ``--promote`` (a code, a category, or
    ``ALL``). Promotion runs last, so a warning already silenced by
    ``ignore`` / ``per-file-ignores`` / ``# noqa`` is gone and never promoted.
    """
    if not promote:
        return results

    promoted_results: list[CheckResult] = []
    for result in results:
        escalated: list[Violation] = []
        kept: list[Violation] = []
        for warning in result.warnings:
            code = _rule_code(warning.rule)
            # ``-000`` codes are skip/parse-error notices ("could not analyse,
            # skipping"), not findings, so promotion (including ``ALL``) leaves
            # them as warnings rather than failing the build on a non-issue.
            if not code.endswith("-000") and _matches(code=code, patterns=promote):
                escalated.append(warning)
            else:
                kept.append(warning)
        violations = [*result.violations, *escalated]
        status = Status.FAIL if violations else (Status.WARN if kept else Status.PASS)
        promoted_results.append(
            CheckResult(
                check=result.check,
                status=status,
                violations=violations,
                warnings=kept,
            )
        )
    return promoted_results
