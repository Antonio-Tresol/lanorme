"""Tests for the docs check (DOCS-001..008), the Markdown structure scanner.

The docs check is opt-in and tree-scoped. It inspects only Markdown under a
configurable ``docs_root`` (default ``docs``); Markdown anywhere else is ignored.
Headings and images inside fenced code blocks are never matched. A false
positive on a genuinely good docs page is the cardinal sin for this check, so
every rule below has a positive (fires) and a negative (clean) case.

NOTE on the fixture idiom: ``DocsCheck`` is *off by default*; ``run`` short-
circuits to PASS when ``enabled`` is False. Every behavioural test therefore
constructs the check with ``enabled=True`` (directly or via ``configure``).
Tests follow AAA structure with inline ``# Arrange / # Act / # Assert`` markers.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from lanorme import Status
from lanorme.checks.docs import DocsCheck


@pytest.fixture
def check() -> DocsCheck:
    """An *enabled* docs check with default settings (docs_root 'docs')."""
    return DocsCheck(enabled=True)


def _write(*, root: Path, name: str, body: str) -> None:
    """Write a Markdown page under *root*, creating parent directories."""
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")


def _codes(*, result) -> list[str]:
    """All violation and warning rule codes in a result, in order."""
    return [v.code for v in result.violations] + [w.code for w in result.warnings]


_GOOD_PAGE = (
    "# Configure checks\n"
    "\n"
    "This how-to shows how to configure checks.\n"
    "\n"
    "## Select rules\n"
    "\n"
    "Some prose about selecting rules.\n"
)


# --------------------------------------------------------------------------- #
# Off-by-default and scoping contracts
# --------------------------------------------------------------------------- #


def test_disabled_by_default_never_fires(tmp_path: Path):
    # Arrange: a default (disabled) check over a page with several violations.
    _write(root=tmp_path, name="docs/how-to/bad.md", body="## no h1\n\n#### skip\n")

    # Act: run without enabling.
    result = DocsCheck().run(src_root=str(tmp_path))

    # Assert: opt-in means silence until configured on.
    assert result.status == Status.PASS
    assert result.violations == []
    assert result.warnings == []


def test_markdown_outside_docs_root_is_ignored(tmp_path: Path, check: DocsCheck):
    # Arrange: a broken page that lives OUTSIDE docs_root.
    _write(root=tmp_path, name="README.md", body="## no h1\n\n#### skip\n")
    _write(root=tmp_path, name="notes/scratch.md", body="no heading at all\n")

    # Act.
    result = check.run(src_root=str(tmp_path))

    # Assert: nothing under docs/, so nothing is reported.
    assert result.status == Status.PASS
    assert _codes(result=result) == []


def test_clean_docs_tree_is_silent(tmp_path: Path, check: DocsCheck):
    # Arrange: a well-formed how-to plus its section index.
    _write(root=tmp_path, name="docs/index.md", body="# Docs\n\nWelcome.\n")
    _write(root=tmp_path, name="docs/how-to/index.md", body="# How-to\n\nGuides.\n")
    _write(root=tmp_path, name="docs/how-to/configure.md", body=_GOOD_PAGE)

    # Act.
    result = check.run(src_root=str(tmp_path))

    # Assert.
    assert result.status == Status.PASS
    assert _codes(result=result) == []


# --------------------------------------------------------------------------- #
# DOCS-001 single-H1
# --------------------------------------------------------------------------- #


def test_docs001_fires_on_two_h1(tmp_path: Path, check: DocsCheck):
    # Arrange: a page with two level-1 headings (one ATX, one setext).
    body = "# First\n\nThis page covers things.\n\nSecond\n======\n\nMore prose.\n"
    _write(root=tmp_path, name="docs/index.md", body=body)

    # Act.
    result = check.run(src_root=str(tmp_path))

    # Assert.
    assert "DOCS-001" in [v.code for v in result.violations]


def test_docs001_fires_on_zero_h1(tmp_path: Path, check: DocsCheck):
    # Arrange: a page that opens at H2 with no H1.
    _write(root=tmp_path, name="docs/index.md", body="## Section\n\nProse.\n")

    # Act.
    result = check.run(src_root=str(tmp_path))

    # Assert.
    assert "DOCS-001" in [v.code for v in result.violations]


def test_docs001_clean_single_h1(tmp_path: Path, check: DocsCheck):
    # Arrange: exactly one H1, with a fenced code block that itself shows a '#'.
    body = "# Title\n\nWelcome.\n\n```python\n# this is a comment, not a heading\n```\n"
    _write(root=tmp_path, name="docs/index.md", body=body)

    # Act.
    result = check.run(src_root=str(tmp_path))

    # Assert.
    assert "DOCS-001" not in _codes(result=result)


# --------------------------------------------------------------------------- #
# DOCS-002 no-skipped-heading-levels
# --------------------------------------------------------------------------- #


def test_docs002_fires_on_skipped_level(tmp_path: Path, check: DocsCheck):
    # Arrange: H1 then H3, skipping H2.
    body = "# Title\n\nThis page explains.\n\n### Deep\n\nProse.\n"
    _write(root=tmp_path, name="docs/index.md", body=body)

    # Act.
    result = check.run(src_root=str(tmp_path))

    # Assert.
    assert "DOCS-002" in [v.code for v in result.violations]


def test_docs002_clean_one_step_descent(tmp_path: Path, check: DocsCheck):
    # Arrange: H1 -> H2 -> H3, descending one step at a time.
    body = "# Title\n\nWelcome.\n\n## A\n\nText.\n\n### A.1\n\nText.\n"
    _write(root=tmp_path, name="docs/index.md", body=body)

    # Act.
    result = check.run(src_root=str(tmp_path))

    # Assert.
    assert "DOCS-002" not in _codes(result=result)


# --------------------------------------------------------------------------- #
# DOCS-003 skimmer-line
# --------------------------------------------------------------------------- #


def test_docs003_fires_on_missing_opener(tmp_path: Path, check: DocsCheck):
    # Arrange: a content page (not index.md) whose first line is not canonical.
    body = "# Configure checks\n\nHere is how you configure checks.\n"
    _write(root=tmp_path, name="docs/how-to/configure.md", body=body)

    # Act.
    result = check.run(src_root=str(tmp_path))

    # Assert.
    assert "DOCS-003" in [v.code for v in result.violations]


def test_docs003_index_page_is_exempt(tmp_path: Path, check: DocsCheck):
    # Arrange: an index.md with no canonical opener is allowed.
    _write(root=tmp_path, name="docs/index.md", body="# Docs\n\nWelcome to the docs.\n")

    # Act.
    result = check.run(src_root=str(tmp_path))

    # Assert.
    assert "DOCS-003" not in _codes(result=result)


def test_docs003_clean_canonical_opener(tmp_path: Path, check: DocsCheck):
    # Arrange: a content page opening with a canonical phrase.
    _write(root=tmp_path, name="docs/how-to/configure.md", body=_GOOD_PAGE)

    # Act.
    result = check.run(src_root=str(tmp_path))

    # Assert.
    assert "DOCS-003" not in _codes(result=result)


# --------------------------------------------------------------------------- #
# DOCS-004 image-alt
# --------------------------------------------------------------------------- #


def test_docs004_fires_on_empty_markdown_alt(tmp_path: Path, check: DocsCheck):
    # Arrange: a Markdown image with empty alt and an <img> with no alt.
    body = (
        "# Title\n\nThis page shows a diagram.\n\n"
        "![](diagram.svg)\n\n"
        "<img src='other.svg'>\n"
    )
    _write(root=tmp_path, name="docs/index.md", body=body)

    # Act.
    result = check.run(src_root=str(tmp_path))

    # Assert: both the empty-alt image and the alt-less tag fire.
    assert [v.code for v in result.violations].count("DOCS-004") == 2


def test_docs004_clean_with_alt_text(tmp_path: Path, check: DocsCheck):
    # Arrange: both images carry descriptive alt text.
    body = (
        "# Title\n\nThis page shows a diagram.\n\n"
        "![a sequence diagram](diagram.svg)\n\n"
        "<img src='other.svg' alt='a flow chart'>\n"
    )
    _write(root=tmp_path, name="docs/index.md", body=body)

    # Act.
    result = check.run(src_root=str(tmp_path))

    # Assert.
    assert "DOCS-004" not in _codes(result=result)


# --------------------------------------------------------------------------- #
# DOCS-005 prefer-svg
# --------------------------------------------------------------------------- #


def test_docs005_warns_on_local_raster(tmp_path: Path, check: DocsCheck):
    # Arrange: a local PNG reference (a remote one and an SVG must not fire).
    body = (
        "# Title\n\nThis page shows pictures.\n\n"
        "![a chart](chart.png)\n\n"
        "![a logo](https://example.com/logo.png)\n\n"
        "![a diagram](diagram.svg)\n"
    )
    _write(root=tmp_path, name="docs/index.md", body=body)

    # Act.
    result = check.run(src_root=str(tmp_path))

    # Assert: only the local raster warns.
    assert [w.code for w in result.warnings].count("DOCS-005") == 1


def test_docs005_allow_list_exempts_raster(tmp_path: Path):
    # Arrange: an allow glob covers the only raster on the page.
    check = DocsCheck(enabled=True, allow=("**/logo.png",))
    body = "# Title\n\nThis page shows a logo.\n\n![a logo](assets/logo.png)\n"
    _write(root=tmp_path, name="docs/index.md", body=body)

    # Act.
    result = check.run(src_root=str(tmp_path))

    # Assert.
    assert "DOCS-005" not in _codes(result=result)


# --------------------------------------------------------------------------- #
# DOCS-006 section-index
# --------------------------------------------------------------------------- #


def test_docs006_warns_on_section_without_index(tmp_path: Path, check: DocsCheck):
    # Arrange: a known section with a page but no index.md.
    _write(root=tmp_path, name="docs/index.md", body="# Docs\n\nWelcome.\n")
    _write(root=tmp_path, name="docs/tutorials/first.md", body=_tutorial())

    # Act.
    result = check.run(src_root=str(tmp_path))

    # Assert.
    assert "DOCS-006" in [w.code for w in result.warnings]


def test_docs006_clean_section_with_index(tmp_path: Path, check: DocsCheck):
    # Arrange: the section carries its index page.
    _write(root=tmp_path, name="docs/index.md", body="# Docs\n\nWelcome.\n")
    _write(root=tmp_path, name="docs/tutorials/index.md", body="# Tutorials\n\nStart here.\n")
    _write(root=tmp_path, name="docs/tutorials/first.md", body=_tutorial())

    # Act.
    result = check.run(src_root=str(tmp_path))

    # Assert.
    assert "DOCS-006" not in _codes(result=result)


# --------------------------------------------------------------------------- #
# DOCS-007 known-quadrant
# --------------------------------------------------------------------------- #


def test_docs007_warns_on_homeless_page(tmp_path: Path, check: DocsCheck):
    # Arrange: a page neither under a known section nor a known top-level page.
    _write(root=tmp_path, name="docs/random.md", body="# Random\n\nThis page wanders.\n")

    # Act.
    result = check.run(src_root=str(tmp_path))

    # Assert.
    assert "DOCS-007" in [w.code for w in result.warnings]


def test_docs007_clean_known_top_level_and_section(tmp_path: Path, check: DocsCheck):
    # Arrange: a known top-level page and a page inside a known section.
    _write(root=tmp_path, name="docs/index.md", body="# Docs\n\nWelcome.\n")
    _write(root=tmp_path, name="docs/reference/configuration.md", body="# Config\n\nKeys.\n")
    _write(root=tmp_path, name="docs/reference/index.md", body="# Reference\n\nIndex.\n")

    # Act.
    result = check.run(src_root=str(tmp_path))

    # Assert.
    assert "DOCS-007" not in _codes(result=result)


# --------------------------------------------------------------------------- #
# DOCS-008 no-numbered-headings
# --------------------------------------------------------------------------- #


def test_docs008_warns_on_numbered_heading(tmp_path: Path, check: DocsCheck):
    # Arrange: an H2 numbered by hand.
    body = "# Title\n\nThis page lists steps.\n\n## 1. Setup\n\nProse.\n"
    _write(root=tmp_path, name="docs/index.md", body=body)

    # Act.
    result = check.run(src_root=str(tmp_path))

    # Assert.
    assert "DOCS-008" in [w.code for w in result.warnings]


def test_docs008_clean_unnumbered_heading(tmp_path: Path, check: DocsCheck):
    # Arrange: an H2 with a plain title, plus a version number that must not fire.
    body = "# Title\n\nThis page lists steps.\n\n## Setup\n\nNeeds 3.13 or newer.\n"
    _write(root=tmp_path, name="docs/index.md", body=body)

    # Act.
    result = check.run(src_root=str(tmp_path))

    # Assert.
    assert "DOCS-008" not in _codes(result=result)


# --------------------------------------------------------------------------- #
# CLI wiring
# --------------------------------------------------------------------------- #


def test_enabled_via_cli_config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys):
    # Arrange: a broken page plus pyproject enabling the check.
    _write(root=tmp_path, name="docs/how-to/configure.md", body="## no h1\n")
    (tmp_path / "pyproject.toml").write_text(
        "[tool.lanorme.docs]\nenabled = true\n", encoding="utf-8"
    )
    from lanorme.cli import main

    # Act.
    monkeypatch.chdir(tmp_path)
    with pytest.raises(SystemExit) as exc:
        main(["check", "."])

    # Assert: the run fails and names the docs rule.
    assert exc.value.code == 1
    assert "DOCS-001" in capsys.readouterr().out


def _tutorial() -> str:
    """A minimal well-formed tutorial content page."""
    return "# First tutorial\n\nThis tutorial walks through the basics.\n"
