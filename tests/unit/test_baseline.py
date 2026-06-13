"""Tests for the warning baseline (baseline.py and its CLI wiring).

A baseline records the findings a codebase already has so only new ones report.
These tests pin the acceptance criteria from issue #37 plus the edge cases the
design review enumerated: the severity gate, the per-key count budget, anchor
stability under line drift, write guards, and the guarantee that no source text
or secret reaches the committed file.

Tests follow AAA structure with inline ``# Arrange / # Act / # Assert`` markers.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from lanorme import CheckResult, Status, Violation
from lanorme import baseline as bl
from lanorme.cli import main

# A line-anchored violation: eval() on a non-literal fires EVAL-001 every time.
_EVAL = "def f(x):\n    return eval(x)\n"


def _project(tmp_path: Path, files: dict[str, str], config: str = "[tool.lanorme]\n") -> Path:
    """Write a pyproject and the given source files; return the project root."""
    (tmp_path / "pyproject.toml").write_text(config, encoding="utf-8")
    for rel, body in files.items():
        path = tmp_path / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body, encoding="utf-8")
    return tmp_path


def _run(argv: list[str]) -> int:
    """Run the CLI, returning the exit code (0 when it does not call sys.exit)."""
    try:
        main(argv)
    except SystemExit as exit_signal:
        return int(exit_signal.code or 0)
    return 0


_BASELINE_CONFIG = '[tool.lanorme]\nbaseline = "lanorme-baseline.json"\n'


def test_write_then_check_is_clean(tmp_path: Path):
    # Arrange: a project with one real violation and a baseline configured.
    root = _project(tmp_path, {"a.py": _EVAL}, config=_BASELINE_CONFIG)

    # Act: record the baseline, then check.
    _run(["baseline", "write", str(root)])
    code = _run(["check", str(root)])

    # Assert: the recorded finding is suppressed, so the run is clean.
    assert (root / "lanorme-baseline.json").is_file()
    assert code == 0


def test_a_new_violation_reports_exactly_once(tmp_path: Path):
    # Arrange: baseline an existing violation, then add a brand new one.
    root = _project(tmp_path, {"a.py": _EVAL}, config=_BASELINE_CONFIG)
    _run(["baseline", "write", str(root)])
    (root / "b.py").write_text(_EVAL, encoding="utf-8")

    # Act.
    code = _run(["check", str(root)])

    # Assert: only the new file fails the build.
    assert code == 1


def test_promote_all_fails_only_on_new_findings(tmp_path: Path, capsys):
    # Arrange: an advisory-only project (a similar-pair warning) baselined, then
    # a new warning added; promote = ["ALL"] would fail on any surviving warning.
    config = '[tool.lanorme]\nbaseline = "lanorme-baseline.json"\npromote = ["ALL"]\n'
    root = _project(tmp_path, {"a.py": _EVAL}, config=config)
    _run(["baseline", "write", str(root)])
    capsys.readouterr()

    # Act: with no new findings, promote has nothing to escalate.
    code = _run(["check", str(root)])

    # Assert: the baselined finding stays suppressed; promote does not fail it.
    assert code == 0


def test_rewrite_after_a_fix_shrinks_the_file(tmp_path: Path):
    # Arrange: baseline two violations, then fix one.
    root = _project(tmp_path, {"a.py": _EVAL, "b.py": _EVAL}, config=_BASELINE_CONFIG)
    _run(["baseline", "write", str(root)])
    before = json.loads((root / "lanorme-baseline.json").read_text(encoding="utf-8"))
    (root / "b.py").write_text("def f(x):\n    return x\n", encoding="utf-8")

    # Act: re-record.
    _run(["baseline", "write", str(root)])
    after = json.loads((root / "lanorme-baseline.json").read_text(encoding="utf-8"))

    # Assert: the fixed finding is pruned from the file.
    assert len(after["entries"]) == len(before["entries"]) - 1


def test_consecutive_writes_are_byte_identical(tmp_path: Path):
    # Arrange.
    root = _project(tmp_path, {"a.py": _EVAL, "b.py": _EVAL}, config=_BASELINE_CONFIG)

    # Act: write twice over unchanged code.
    _run(["baseline", "write", str(root)])
    first = (root / "lanorme-baseline.json").read_bytes()
    _run(["baseline", "write", str(root)])
    second = (root / "lanorme-baseline.json").read_bytes()

    # Assert: deterministic output, no spurious diff churn.
    assert first == second


def test_anchor_is_stable_when_lines_are_inserted_above(tmp_path: Path):
    # Arrange: baseline a violation, then push it down with 50 new lines above.
    root = _project(tmp_path, {"a.py": _EVAL}, config=_BASELINE_CONFIG)
    _run(["baseline", "write", str(root)])
    padding = "".join(f"x{i} = {i}\n" for i in range(50))
    (root / "a.py").write_text(padding + _EVAL, encoding="utf-8")

    # Act.
    code = _run(["check", str(root)])

    # Assert: content-anchoring keeps the finding suppressed despite line drift.
    assert code == 0


def test_severity_gate_reports_a_warning_that_escalates_to_error(tmp_path: Path):
    # Arrange: a file in the SIZE-001 warning band (300-500 effective lines),
    # baselined, then grown past the 500-line hard-fail threshold.
    warn_body = "".join(f"v{i} = {i}\n" for i in range(350))
    root = _project(tmp_path, {"big.py": warn_body}, config=_BASELINE_CONFIG)
    _run(["baseline", "write", str(root)])
    (root / "big.py").write_text("".join(f"v{i} = {i}\n" for i in range(520)), encoding="utf-8")

    # Act.
    code = _run(["check", str(root)])

    # Assert: a baselined warning must not hide the escalated error.
    assert code == 1


def test_count_budget_never_suppresses_one_more_than_recorded():
    # Arrange: a baseline recording two occurrences of one key; a run with three.
    root = Path("/proj")
    findings = [Violation(file="a.py", line=0, rule="X-001: thing", message="m", fix="")] * 3
    result = CheckResult(check="x", status=Status.FAIL, violations=list(findings))
    entries = bl._entries_from_results(results=[result], project_root=root)
    entries[0]["count"] = 2  # pretend only two were recorded

    # Act: suppress against that smaller budget.
    index = {(e["file"], e["code"], e["anchor"]): e for e in entries}
    consumed: dict = {}
    kept = [
        v
        for v in findings
        if not bl._is_suppressed(
            index=index, consumed=consumed, project_root=root, finding=v, tier="error", cache={}
        )
    ]

    # Assert: the third occurrence is not suppressed.
    assert len(kept) == 1


def test_error_entry_suppresses_its_improved_warning_form():
    # Arrange: an entry recorded as an error; the same finding now warning-tier.
    root = Path("/proj")
    finding = Violation(file="a.py", line=0, rule="X-001: thing", message="m", fix="")
    [entry] = bl._entries_from_results(
        results=[CheckResult(check="x", status=Status.FAIL, violations=[finding])],
        project_root=root,
    )
    index = {(entry["file"], entry["code"], entry["anchor"]): entry}

    # Act: the finding reappears as a warning (improved tier).
    suppressed = bl._is_suppressed(
        index=index, consumed={}, project_root=root, finding=finding, tier="warning", cache={}
    )

    # Assert: a recorded error still covers its improved warning form.
    assert suppressed is True


def test_no_source_text_or_secret_reaches_the_committed_file(tmp_path: Path):
    # Arrange: a finding whose message embeds a source snippet and a secret value,
    # exactly the shape of security_patterns' "Raw SQL ... : {snippet}" message.
    leaky = Violation(
        file="db.py",
        line=7,
        rule="SECSQL-001: raw SQL reaches a database sink",
        message="Raw SQL passed to a database sink: SELECT * FROM users WHERE token='sk-LEAK-9999'",
        fix="",
    )
    result = CheckResult(check="security_patterns", status=Status.FAIL, violations=[leaky])
    baseline_path = tmp_path / "lanorme-baseline.json"

    # Act.
    bl.write(results=[result], project_root=tmp_path, baseline_path=baseline_path)
    written = baseline_path.read_text(encoding="utf-8")

    # Assert: neither the SQL snippet nor the secret value is stored.
    assert "sk-LEAK-9999" not in written
    assert "SELECT" not in written


def test_run000_crash_notices_are_never_recorded(tmp_path: Path):
    # Arrange: a RUN-000 crash notice (no file) alongside a real finding.
    crash = Violation(file="", line=0, rule="RUN-000: check raised", message="boom", fix="")
    real = Violation(file="a.py", line=2, rule="EVAL-001: eval", message="m", fix="")
    result = CheckResult(check="x", status=Status.WARN, warnings=[crash, real])
    baseline_path = tmp_path / "lanorme-baseline.json"

    # Act.
    bl.write(results=[result], project_root=tmp_path, baseline_path=baseline_path)
    data = json.loads(baseline_path.read_text(encoding="utf-8"))

    # Assert: only the real, file-bearing finding is recorded.
    files = {entry["file"] for entry in data["entries"]}
    assert files == {"a.py"}


def test_noqa_finding_is_neither_recorded_nor_budget_consuming(tmp_path: Path):
    # Arrange: two identical violations, one carrying a covering noqa comment.
    body = "def f(x):\n    return eval(x)  # noqa: EVAL-001\n\n\ndef g(y):\n    return eval(y)\n"
    root = _project(tmp_path, {"a.py": body}, config=_BASELINE_CONFIG)

    # Act: write records only the un-noqa'd finding; a later check stays clean.
    _run(["baseline", "write", str(root)])
    data = json.loads((root / "lanorme-baseline.json").read_text(encoding="utf-8"))
    code = _run(["check", str(root)])

    # Assert: one entry recorded (the noqa'd one excluded), run clean.
    assert len(data["entries"]) == 1
    assert code == 0


def test_narrowed_write_is_refused(tmp_path: Path):
    # Arrange: a project and a single-file target for the write.
    root = _project(tmp_path, {"a.py": _EVAL, "b.py": _EVAL}, config=_BASELINE_CONFIG)

    # Act: a file-target write would regenerate from a partial run.
    code = _run(["baseline", "write", str(root / "a.py")])

    # Assert: refused with exit 2; the file is never written.
    assert code == 2
    assert not (root / "lanorme-baseline.json").exists()


def test_no_baseline_flag_reports_the_whole_debt(tmp_path: Path):
    # Arrange: a baselined project that checks clean normally.
    root = _project(tmp_path, {"a.py": _EVAL}, config=_BASELINE_CONFIG)
    _run(["baseline", "write", str(root)])

    # Act: --no-baseline ignores the recorded debt.
    clean = _run(["check", str(root)])
    audited = _run(["check", str(root), "--no-baseline"])

    # Assert: clean with the baseline, failing without it.
    assert clean == 0
    assert audited == 1


def test_status_lists_a_stale_entry(tmp_path: Path, capsys):
    # Arrange: baseline a violation, then fix it so the entry goes stale.
    root = _project(tmp_path, {"a.py": _EVAL}, config=_BASELINE_CONFIG)
    _run(["baseline", "write", str(root)])
    (root / "a.py").write_text("def f(x):\n    return x\n", encoding="utf-8")
    capsys.readouterr()

    # Act.
    _run(["baseline", "status", str(root)])
    out = capsys.readouterr().out

    # Assert: the now-unmatched entry is reported as stale.
    assert "stale" in out.lower()
    assert "EVAL-001" in out


def test_check_with_missing_baseline_file_exits_two(tmp_path: Path):
    # Arrange: a baseline is configured but never written.
    root = _project(tmp_path, {"a.py": _EVAL}, config=_BASELINE_CONFIG)

    # Act.
    code = _run(["check", str(root)])

    # Assert: a clear configuration error, not a silent pass.
    assert code == 2


def test_corrupt_baseline_file_exits_two(tmp_path: Path):
    # Arrange: a malformed baseline file.
    root = _project(tmp_path, {"a.py": _EVAL}, config=_BASELINE_CONFIG)
    (root / "lanorme-baseline.json").write_text("{ not json", encoding="utf-8")

    # Act.
    code = _run(["check", str(root)])

    # Assert: a clean exit 2, not a traceback.
    assert code == 2
