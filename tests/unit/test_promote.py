"""Tests for promoting advisory warnings to build-failing errors.

A heuristic rule (TYPE-004, SIMILAR-001, ...) ships as a default-on warning so
it never breaks a build unasked. A project that wants it enforced lists its
code or category under ``[tool.lanorme] promote`` (or passes ``--promote``),
which moves the matching warnings into violations and flips the exit code.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from lanorme import CheckResult, Status, Violation
from lanorme.cli import _config_list, main
from lanorme.filtering import _apply_promotions, _matches


def _finding(code: str) -> Violation:
    return Violation(file="m.py", line=1, rule=f"{code}: detail", message="m", fix="f")


def _result(*, violations: list[Violation], warnings: list[Violation]) -> CheckResult:
    status = Status.FAIL if violations else (Status.WARN if warnings else Status.PASS)
    return CheckResult(check="c", status=status, violations=violations, warnings=warnings)


def test_promote_by_exact_code_moves_warning_to_violation():
    # Arrange.
    result = _result(violations=[], warnings=[_finding("TYPE-004")])

    # Act.
    promoted = _apply_promotions(results=[result], promote=["TYPE-004"])

    # Assert.
    assert promoted[0].status == Status.FAIL
    assert len(promoted[0].violations) == 1
    assert not promoted[0].warnings


def test_promote_by_category_matches():
    # Arrange / Act.
    result = _result(violations=[], warnings=[_finding("TYPE-004")])
    promoted = _apply_promotions(results=[result], promote=["TYPE"])

    # Assert.
    assert promoted[0].status == Status.FAIL


def test_promote_all_escalates_every_warning():
    # Arrange.
    result = _result(violations=[], warnings=[_finding("TYPE-004"), _finding("SIMILAR-001")])

    # Act.
    promoted = _apply_promotions(results=[result], promote=["ALL"])

    # Assert.
    assert len(promoted[0].violations) == 2
    assert not promoted[0].warnings


def test_unmatched_code_stays_a_warning():
    # Arrange / Act.
    result = _result(violations=[], warnings=[_finding("TYPE-004")])
    promoted = _apply_promotions(results=[result], promote=["DRY-001"])

    # Assert.
    assert promoted[0].status == Status.WARN
    assert promoted[0].warnings and not promoted[0].violations


def test_empty_promote_is_a_noop():
    # Arrange / Act.
    result = _result(violations=[], warnings=[_finding("TYPE-004")])
    promoted = _apply_promotions(results=[result], promote=[])

    # Assert: same object, untouched.
    assert promoted[0] is result


def test_promoted_warning_joins_existing_violations():
    # Arrange: a real violation already present alongside the warning.
    result = _result(violations=[_finding("SQL-001")], warnings=[_finding("TYPE-004")])

    # Act.
    promoted = _apply_promotions(results=[result], promote=["TYPE-004"])

    # Assert.
    assert len(promoted[0].violations) == 2
    assert not promoted[0].warnings


_POSITIVE = "def get_user(id: int):\n    return db.get(id)\n"


def test_default_warning_does_not_fail_the_build(tmp_path: Path, capsys):
    # Arrange.
    (tmp_path / "svc.py").write_text(_POSITIVE, encoding="utf-8")

    # Act: a TYPE-004 warning alone must not raise SystemExit.
    main(["check", str(tmp_path), "--check", "strong_types", "--json"])

    # Assert: it surfaced as a warning, not an error.
    out = capsys.readouterr().out
    assert "TYPE-004" in out


def test_config_promote_makes_the_build_fail(tmp_path: Path, capsys):
    # Arrange: the project promotes TYPE-004 via pyproject.
    (tmp_path / "pyproject.toml").write_text(
        '[tool.lanorme]\npromote = ["TYPE-004"]\n', encoding="utf-8"
    )
    (tmp_path / "svc.py").write_text(_POSITIVE, encoding="utf-8")

    # Act / Assert.
    with pytest.raises(SystemExit) as exc:
        main(["check", str(tmp_path), "--check", "strong_types", "--json"])
    assert exc.value.code == 1


def test_cli_promote_flag_makes_the_build_fail(tmp_path: Path, capsys):
    # Arrange.
    (tmp_path / "svc.py").write_text(_POSITIVE, encoding="utf-8")

    # Act / Assert.
    with pytest.raises(SystemExit) as exc:
        main(["check", str(tmp_path), "--check", "strong_types", "--promote", "TYPE-004", "--json"])
    assert exc.value.code == 1


# --- red-team regressions: normalisation, skip notices, ordering, show-config ---


def test_matches_is_case_insensitive_and_strips():
    # Arrange: codes are uppercase, but a selector may carry stray case/whitespace.
    # Act / Assert: it still matches, like the CLI form normalised by _csv.
    assert _matches(code="TYPE-004", patterns=["type-004"])
    assert _matches(code="TYPE-004", patterns=[" TYPE-004 "])
    assert _matches(code="TYPE-004", patterns=["all"])
    assert not _matches(code="TYPE-004", patterns=["", "  "])


def test_config_list_accepts_a_bare_string():
    # Arrange: `promote = "ALL"` must not iterate into ['A', 'L', 'L'].
    # Act / Assert.
    assert _config_list("ALL") == ["ALL"]
    assert _config_list(["TYPE-004"]) == ["TYPE-004"]
    assert _config_list(None) == []
    assert _config_list(5) == []


def test_skip_notice_is_not_promoted_even_by_all():
    # Arrange: a `-000` skip/parse-error notice is not a finding.
    result = _result(violations=[], warnings=[_finding("TYPE-000")])

    # Act.
    promoted = _apply_promotions(results=[result], promote=["ALL"])

    # Assert: ALL must leave it a warning.
    assert promoted[0].status == Status.WARN
    assert not promoted[0].violations


def test_bare_string_promote_in_config_fails_the_build(tmp_path: Path, capsys):
    # Arrange.
    (tmp_path / "pyproject.toml").write_text('[tool.lanorme]\npromote = "ALL"\n', encoding="utf-8")
    (tmp_path / "svc.py").write_text(_POSITIVE, encoding="utf-8")

    # Act / Assert.
    with pytest.raises(SystemExit) as exc:
        main(["check", str(tmp_path), "--check", "strong_types", "--json"])
    assert exc.value.code == 1


def test_ignored_warning_is_not_promoted(tmp_path: Path, capsys):
    # Arrange: the same code is both ignored and promoted; ignore drops it first.
    (tmp_path / "pyproject.toml").write_text(
        '[tool.lanorme]\nignore = ["TYPE-004"]\npromote = ["TYPE-004"]\n', encoding="utf-8"
    )
    (tmp_path / "svc.py").write_text(_POSITIVE, encoding="utf-8")

    # Act: no SystemExit means the build passed (the warning was filtered, not promoted).
    main(["check", str(tmp_path), "--check", "strong_types", "--json"])


def test_show_config_surfaces_promote(tmp_path: Path, capsys):
    # Arrange.
    (tmp_path / "pyproject.toml").write_text('[tool.lanorme]\npromote = ["TYPE-004"]\n', encoding="utf-8")
    (tmp_path / "svc.py").write_text(_POSITIVE, encoding="utf-8")

    # Act.
    main(["check", str(tmp_path), "--show-config"])

    # Assert: the build-failing setting is visible in the dump.
    assert "promote" in capsys.readouterr().out
