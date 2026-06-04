"""Tests for the CLI config-wiring the unit checks cannot exercise directly.

These lock the parts that live in ``cli.py``: that ``source_root`` is injected
into the two layout-aware checks and *only* those, and that a configured
``exclude`` reaches the discovery layer through ``main``.
"""

from __future__ import annotations

from pathlib import Path

from lanorme import CheckResult, Status, Violation, _registry, discovery, get_check, register
from lanorme.cli import _apply_check_config, main
from lanorme.reporting import _emit_github


class _Spy:
    """A throwaway configurable check that records the settings it is handed."""

    name = "spy_check"
    description = "records settings"
    rules: list[str] = []

    def __init__(self) -> None:
        self.received: dict[str, object] | None = None

    def configure(self, *, settings: dict[str, object]) -> None:
        self.received = dict(settings)


def test_source_root_injected_only_into_layout_checks():
    # Arrange: a spy stands in for a generic configurable check.
    spy = _Spy()
    register(spy)
    try:
        # Act.
        _apply_check_config(
            config={
                "source_root": "src/pkg",
                "layer_deps": {"composition_root": ["api/dependencies.py"]},
                "spy_check": {"some_key": 1},
            }
        )

        # Assert: the two layout-aware checks receive it; the spy does not.
        assert get_check("layer_deps").source_root == "src/pkg"
        assert get_check("port_coverage").source_root == "src/pkg"
        assert spy.received == {"some_key": 1}
        assert "source_root" not in spy.received
    finally:
        _registry.pop("spy_check", None)


def test_main_publishes_configured_excludes_to_discovery(tmp_path: Path, capsys):
    # Arrange: a project that configures an exclude glob.
    (tmp_path / "pyproject.toml").write_text(
        '[tool.lanorme]\nexclude = ["vendor/*"]\n', encoding="utf-8"
    )
    (tmp_path / "mod.py").write_text("x = 1\n", encoding="utf-8")

    # Act: run the real CLI entry point (it may exit nonzero on findings).
    try:
        main(["check", str(tmp_path), "--json"])
    except SystemExit:
        pass

    # Assert: the configured glob reached the discovery layer, not just output.
    assert "vendor/*" in discovery.active_excludes()


def test_show_config_reports_source_and_opt_in_state(tmp_path: Path, capsys):
    # Arrange: a project with no config (built-in defaults).
    (tmp_path / "mod.py").write_text("x = 1\n", encoding="utf-8")

    # Act: --show-config prints and returns without running checks.
    main(["check", str(tmp_path), "--show-config"])
    out = capsys.readouterr().out

    # Assert: it names the config source and flags an opt-in check as not enabled.
    assert "config file:" in out
    assert "attribute_access" in out
    assert "(opt-in, not enabled)" in out


# --------------------------------------------------------------------------- #
# GitHub annotations output format
# --------------------------------------------------------------------------- #

def _make_result(*, violations=(), warnings=()):
    status = Status.FAIL if violations else (Status.WARN if warnings else Status.PASS)
    return CheckResult(check="test_check", status=status, violations=list(violations), warnings=list(warnings))


def test_github_format_violations(capsys):
    # Arrange: a single violation.
    v = Violation(file="src/foo.py", line=42, rule="SQL-001", message="raw query", fix="use ORM")

    # Act.
    _emit_github(results=[_make_result(violations=[v])])

    # Assert: emits the ::error workflow command with correct fields.
    out = capsys.readouterr().out
    assert "::error file=src/foo.py,line=42,title=SQL-001::raw query" in out


def test_github_format_title_uses_code_not_full_rule(capsys):
    # Arrange: a real rule string carrying a ': ' description and a comma, which
    # would corrupt the comma-separated, '::'-terminated annotation properties.
    v = Violation(
        file="src/foo.py",
        line=9,
        rule="DRY-001: Near-duplicate function body, refactor",
        message="duplicate of bar()",
        fix="extract a helper",
    )

    # Act.
    _emit_github(results=[_make_result(violations=[v])])

    # Assert: the title is the bare code; the description never reaches the
    # annotation, so no stray property or terminator is introduced.
    out = capsys.readouterr().out
    assert "title=DRY-001::duplicate of bar()" in out
    assert "Near-duplicate" not in out


def test_github_format_escapes_newlines_in_message(capsys):
    # Arrange: a multi-line message, which must not break the single-line command.
    v = Violation(file="a.py", line=1, rule="X-001", message="line one\nline two", fix="f")

    # Act.
    _emit_github(results=[_make_result(violations=[v])])

    # Assert: the newline is encoded, keeping the command on one line.
    out = capsys.readouterr().out
    assert "::error file=a.py,line=1,title=X-001::line one%0Aline two" in out


def test_github_format_warnings(capsys):
    # Arrange: a single warning.
    w = Violation(file="src/bar.py", line=7, rule="CMT-001", message="missing docstring", fix="add one")

    # Act.
    _emit_github(results=[_make_result(warnings=[w])])

    # Assert: emits the ::warning workflow command with correct fields.
    out = capsys.readouterr().out
    assert "::warning file=src/bar.py,line=7,title=CMT-001::missing docstring" in out


def test_github_format_flag(tmp_path: Path, capsys):
    # Arrange: a minimal project with no findings.
    (tmp_path / "mod.py").write_text("x = 1\n", encoding="utf-8")

    # Act: pass --output-format github explicitly.
    try:
        main(["check", str(tmp_path), "--output-format", "github"])
    except SystemExit:
        pass

    # Assert: no annotation lines emitted for a clean project.
    out = capsys.readouterr().out
    assert "::error" not in out
    assert "::warning" not in out


def test_github_autodetect_via_env(tmp_path: Path, capsys, monkeypatch):
    # Arrange: simulate running inside GitHub Actions.
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    (tmp_path / "mod.py").write_text("x = 1\n", encoding="utf-8")

    # Act: run without --output-format; should auto-detect the env var.
    try:
        main(["check", str(tmp_path)])
    except SystemExit:
        pass

    # Assert: concise/full-format summary lines must not appear; only annotation
    # lines are valid output under the github format.
    out = capsys.readouterr().out
    assert "All " not in out  # concise summary footer
    assert "Summary:" not in out  # concise summary footer with findings
