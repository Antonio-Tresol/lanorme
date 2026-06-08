"""Tests for the comments check (CMT-001, CMT-002) and its parse guard.

The regression of note: ``_comment_parses_as_code`` runs ``ast.parse`` on text
built from a comment and previously caught only ``(SyntaxError, ValueError)``.
A deeply nested but parseable expression in a single comment can overflow the
parser and raise ``RecursionError``, crashing the whole check. Such a comment
must be treated as prose (not commented-out code), never fatal.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from lanorme import Status
from lanorme.checks import comments as comments_module
from lanorme.checks.comments import CommentsCheck, _comment_parses_as_code

# A single-line expression nested far enough to overflow a recursion-bounded
# parser, yet syntactically valid where it does parse.
_DEEP_EXPRESSION = "(" + "[" * 200 + "]" * 200 + ")"


@pytest.fixture
def check() -> CommentsCheck:
    """A comments check with default thresholds (block 6 lines, line 120 chars)."""
    return CommentsCheck()


def _write(*, root: Path, name: str, body: str) -> None:
    """Write a Python source file under *root*."""
    (root / name).write_text(body, encoding="utf-8")


def test_deep_comment_expression_does_not_crash(check: CommentsCheck, tmp_path: Path):
    # Arrange: force ``ast.parse`` to raise RecursionError as a recursion-bounded
    # build would, then feed the helper a deep expression directly.
    def _boom(_source: str) -> ast.Module:
        raise RecursionError("maximum recursion depth exceeded")

    # Act + Assert: the guard swallows it and reports "not code", never raising.
    monkeypatched = comments_module.ast.parse
    comments_module.ast.parse = _boom
    try:
        result = _comment_parses_as_code(_DEEP_EXPRESSION)
    finally:
        comments_module.ast.parse = monkeypatched

    assert result is False


def test_deep_comment_in_file_completes_without_flagging(check: CommentsCheck, tmp_path: Path):
    # Arrange: a real file whose comment is a deep parseable expression, beside
    # ordinary code. On any interpreter the run must finish.
    _write(root=tmp_path, name="deep.py", body=f"# {_DEEP_EXPRESSION}\nx = 1\n")

    # Act: the run must complete rather than raise RecursionError.
    result = check.run(src_root=str(tmp_path))

    # Assert: the deep comment is not mistaken for commented-out code (it may
    # still trip the unrelated over-long-line rule, which is fine here).
    assert result.check == "comments"
    assert not any(v.rule == "CMT-001" for v in result.violations)


def test_cmt001_flags_commented_out_code(check: CommentsCheck, tmp_path: Path):
    # Arrange: a standalone comment that is really an assignment statement.
    _write(root=tmp_path, name="dead.py", body="x = 1\n# y = x + 2\n")

    # Act.
    result = check.run(src_root=str(tmp_path))

    # Assert.
    assert result.status == Status.FAIL
    assert any(v.rule == "CMT-001" for v in result.violations)


def test_cmt001_ignores_prose(check: CommentsCheck, tmp_path: Path):
    # Arrange: a sentence-shaped comment that is prose, not code.
    _write(root=tmp_path, name="prose.py", body="# this is a real explanation.\nx = 1\n")

    # Act.
    result = check.run(src_root=str(tmp_path))

    # Assert.
    assert result.status == Status.PASS
    assert not result.violations


_PEP723_BLOCK = (
    "# /// script\n"
    '# requires-python = ">=3.13"\n'
    '# dependencies = ["requests", "rich"]\n'
    "# ///\n"
)


def test_cmt001_skips_pep723_inline_metadata(check: CommentsCheck, tmp_path: Path):
    # Arrange: a PEP 723 block whose `dependencies = [...]` line parses as an
    # assignment, beside ordinary code.
    _write(root=tmp_path, name="script.py", body=f"{_PEP723_BLOCK}import sys\n\nprint(sys.argv)\n")

    # Act.
    result = check.run(src_root=str(tmp_path))

    # Assert: the metadata block is tooling, not commented-out code.
    assert not any(v.rule == "CMT-001" for v in result.violations)


def test_cmt001_still_flags_dead_code_outside_pep723_block(check: CommentsCheck, tmp_path: Path):
    # Arrange: real commented-out code follows a valid PEP 723 block; the skip
    # must be scoped to the block, not the rest of the file.
    _write(root=tmp_path, name="script.py", body=f"{_PEP723_BLOCK}import sys\n\n# y = sys.argv[0]\n")

    # Act.
    result = check.run(src_root=str(tmp_path))

    # Assert: the block is exempt, the trailing dead-code line is not.
    flagged = [v for v in result.violations if v.rule == "CMT-001"]
    assert len(flagged) == 1
    assert "y = sys.argv[0]" in flagged[0].message


def test_pep723_metadata_lines_requires_a_closing_fence():
    # Arrange: an opener with no `# ///` close is not a metadata block.
    lines = ['# /// script', '# dependencies = ["rich"]', "import sys"]

    # Act.
    metadata = comments_module._pep723_metadata_lines(lines)

    # Assert: nothing is treated as metadata, so the deps line stays lintable.
    assert metadata == frozenset()


def test_cmt002_flags_overlong_block(check: CommentsCheck, tmp_path: Path):
    # Arrange: seven consecutive standalone comment lines, one past the limit of six.
    block = "".join(f"# note number {i}\n" for i in range(7))
    _write(root=tmp_path, name="block.py", body=block + "x = 1\n")

    # Act.
    result = check.run(src_root=str(tmp_path))

    # Assert.
    assert result.status == Status.FAIL
    block_hits = [v for v in result.violations if v.rule == "CMT-002" and "block" in v.message]
    assert len(block_hits) == 1
    assert "7 lines" in block_hits[0].message


def test_cmt002_block_at_limit_is_allowed(check: CommentsCheck, tmp_path: Path):
    # Arrange: a comment block of exactly the limit (six lines) is the boundary.
    block = "".join(f"# note number {i}\n" for i in range(6))
    _write(root=tmp_path, name="edge.py", body=block + "x = 1\n")

    # Act.
    result = check.run(src_root=str(tmp_path))

    # Assert.
    assert result.status == Status.PASS
    assert not any(v.rule == "CMT-002" for v in result.violations)


def test_cmt002_flags_overlong_line(check: CommentsCheck, tmp_path: Path):
    # Arrange: a single comment whose text exceeds the 120-character limit.
    long_text = "x" * 130
    _write(root=tmp_path, name="long.py", body=f"# {long_text}\nvalue = 1\n")

    # Act.
    result = check.run(src_root=str(tmp_path))

    # Assert.
    assert result.status == Status.FAIL
    line_hits = [v for v in result.violations if v.rule == "CMT-002" and "chars" in v.message]
    assert len(line_hits) == 1
    assert "130 chars" in line_hits[0].message
