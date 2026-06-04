"""Tests for DRY-001 exact structural clone detection.

The regression of note: a single deeply nested file overflowed the ``deepcopy``
used to normalise a function body and crashed the whole run. One bad file must be
skipped, not fatal, and the rest of the tree must still be checked.
"""

from __future__ import annotations

from pathlib import Path

from lanorme import Status
from lanorme.checks.duplication import DuplicationCheck

_DUP_BODY = (
    "def {name}(a, b):\n"
    "    total = 0\n"
    "    total = a + b\n"
    "    total = total + 1\n"
    "    total = total - 0\n"
    "    return total\n"
)


def test_deeply_nested_file_is_skipped_not_crashed(tmp_path: Path):
    # Arrange: a file that parses but overflows deepcopy during normalisation
    # (depth 250: above the deepcopy limit, below the parser limit), beside a
    # genuine duplicate pair.
    (tmp_path / "deep.py").write_text(
        "def f():\n    return " + "[" * 250 + "]" * 250 + "\n", encoding="utf-8"
    )
    (tmp_path / "a.py").write_text(_DUP_BODY.format(name="alpha"), encoding="utf-8")
    (tmp_path / "b.py").write_text(_DUP_BODY.format(name="beta"), encoding="utf-8")

    # Act: the run must complete rather than raise RecursionError.
    result = DuplicationCheck().run(src_root=str(tmp_path))

    # Assert: the deep file is skipped with a DRY-000 warning, and the genuine
    # duplicate is still detected.
    assert result.status == Status.FAIL
    assert any(w.rule.startswith("DRY-000") for w in result.warnings)
    assert any(v.rule.startswith("DRY-001") for v in result.violations)


def test_clean_tree_has_no_findings(tmp_path: Path):
    # Arrange: two distinct functions, no duplication.
    (tmp_path / "a.py").write_text(_DUP_BODY.format(name="alpha"), encoding="utf-8")
    (tmp_path / "b.py").write_text(
        "def beta(x):\n    return x * 2\n", encoding="utf-8"
    )

    # Act.
    result = DuplicationCheck().run(src_root=str(tmp_path))

    # Assert.
    assert result.status == Status.PASS
    assert not result.violations
