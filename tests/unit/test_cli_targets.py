"""Regression tests for path-target handling in the ``check`` command.

Issue #17: ``lanorme check <file.py>`` silently reported zero findings while
``lanorme check <dir>`` on the same tree fired, because ``os.walk`` over a file
yields nothing. These lock the fix: a file target is walked via its surrounding
directory and the findings are narrowed back to the requested path(s), so a file
target reports exactly what the directory run reports for that file.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from lanorme.cli import main

_CONFIG = (
    "[tool.lanorme.domain_terms]\n"
    "[[tool.lanorme.domain_terms.rules]]\n"
    'id = "TERM-002"\n'
    'canonical = "Business"\n'
    'forbidden = ["Brand"]\n'
)


def _project(tmp_path: Path) -> Path:
    """Write a project whose vocabulary forbids 'Brand', with two offending files."""
    (tmp_path / "pyproject.toml").write_text(_CONFIG, encoding="utf-8")
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    (pkg / "models.py").write_text("class Brand:\n    pass\n", encoding="utf-8")
    (pkg / "other.py").write_text("class Brand:\n    pass\n", encoding="utf-8")
    return pkg


def _domain_terms_findings(capsys) -> list[dict]:
    """Parse the captured ``--json`` output into the domain_terms violation list."""
    payload = json.loads(capsys.readouterr().out)
    by_name = {result["check"]: result for result in payload}
    return by_name["domain_terms"]["violations"]


def _run(target: Path | list[Path], capsys) -> list[dict]:
    """Run ``check --check domain_terms --json`` on *target* and return its findings."""
    targets = [str(target)] if isinstance(target, Path) else [str(t) for t in target]
    with pytest.raises(SystemExit):  # nonzero exit on the findings we expect
        main(["check", *targets, "--check", "domain_terms", "--json"])
    return _domain_terms_findings(capsys)


def _signature(findings: list[dict], *, basename: str | None = None) -> set[tuple[int, str]]:
    """Reduce findings to (line, rule) keys, optionally restricted to one file."""
    chosen = findings if basename is None else [f for f in findings if f["file"].endswith(basename)]
    return {(f["line"], f["rule"]) for f in chosen}


def test_file_target_reports_what_the_directory_reports(tmp_path: Path, capsys):
    # Arrange.
    pkg = _project(tmp_path)

    # Act: the same tree, addressed as a directory and as one file inside it.
    from_dir = _run(tmp_path, capsys)
    from_file = _run(pkg / "models.py", capsys)

    # Assert: the file target fires (issue #17 = it silently found zero) and its
    # findings equal what the directory run found for that same file.
    assert _signature(from_file)
    assert _signature(from_file) == _signature(from_dir, basename="models.py")


def test_file_target_excludes_sibling_findings(tmp_path: Path, capsys):
    # Arrange: both files offend; only one is requested.
    pkg = _project(tmp_path)

    # Act.
    from_file = _run(pkg / "models.py", capsys)

    # Assert: the sibling that was walked-for-context is not reported.
    assert from_file
    assert not any(f["file"].endswith("other.py") for f in from_file)


def test_multiple_file_targets_are_all_reported(tmp_path: Path, capsys):
    # Arrange.
    pkg = _project(tmp_path)

    # Act: request both files explicitly.
    findings = _run([pkg / "models.py", pkg / "other.py"], capsys)

    # Assert: both contribute findings.
    files = {Path(f["file"]).name for f in findings}
    assert files == {"models.py", "other.py"}


def test_missing_path_exits_two(tmp_path: Path, capsys):
    # Arrange / Act / Assert.
    with pytest.raises(SystemExit) as exc:
        main(["check", str(tmp_path / "nope.py"), "--check", "domain_terms"])
    assert exc.value.code == 2
    assert "does not exist" in capsys.readouterr().err
