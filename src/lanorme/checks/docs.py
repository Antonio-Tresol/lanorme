"""DOCS-001..008: structure and accessibility for a Markdown docs tree.

An opt-in, tree-scoped check that enforces a familiar Diataxis-style structure on
Markdown documentation. It inspects only Markdown under a configurable
``docs_root`` (default ``docs``); files anywhere else are ignored, so it never
imposes a docs structure on source trees or stray Markdown::

    DOCS-001  single-H1: a content page has exactly one level-1 heading.        [error]
    DOCS-002  no-skipped-heading-levels: headings descend one level at a time.   [error]
    DOCS-003  skimmer-line: a content page opens with a canonical first line.    [error]
    DOCS-004  image-alt: every image carries alternative text.                   [error]
    DOCS-005  prefer-svg: a local raster image should be SVG or Mermaid.         [warning]
    DOCS-006  section-index: a known section directory carries an index page.    [warning]
    DOCS-007  known-quadrant: every page has a home in the architecture.         [warning]
    DOCS-008  no-numbered-headings: authors do not number headings by hand.      [warning]

Headings and images inside fenced code blocks (``` ... ```) are never matched,
so a code sample that shows ``# heading`` or ``![](x.png)`` is left alone.

Off by default. Enable it once your docs follow the architecture::

    [tool.lanorme.docs]
    enabled = true
    docs_root = "docs"                         # default "docs"
    sections = ["tutorials", "how-to", "reference", "explanation"]
    raster_extensions = ["png", "jpg", "jpeg", "gif", "webp", "bmp"]
    allow = ["**/logo.png"]                    # globs exempt from prefer-svg

Run:
    lanorme check . --check=docs
"""

from __future__ import annotations

import fnmatch
import re
from dataclasses import dataclass, field
from pathlib import Path

from lanorme import CheckResult, Status, Violation, register
from lanorme.discovery import iter_files

# Vendored or generated directories that are never part of a docs tree.
_SKIP_PARTS = frozenset(
    {".git", ".venv", "venv", "node_modules", "__pycache__", "dist", "build"}
)

# An ATX heading: one to six leading hashes, a space, then a non-empty title.
_ATX_RE = re.compile(r"^(#{1,6})\s+(\S.*)$")

# A setext underline: a run of '=' (H1) or '-' (H2) under a text line.
_SETEXT_H1_RE = re.compile(r"^=+\s*$")
_SETEXT_H2_RE = re.compile(r"^-+\s*$")

# A Markdown image: ![alt](target). The alt run stops at the first ']'.
_MD_IMAGE_RE = re.compile(r"!\[([^\]]*)\]\(([^)\s]+)")

# An <img ...> tag, captured to its first '>'.
_IMG_TAG_RE = re.compile(r"<img\b([^>]*)>", re.IGNORECASE)
_ALT_ATTR_RE = re.compile(r"""\balt\s*=\s*("([^"]*)"|'([^']*)')""", re.IGNORECASE)

# A URL scheme prefix marks a non-local reference (http://, mailto:, data:).
_SCHEME_RE = re.compile(r"^[a-z][a-z0-9+.-]*://", re.IGNORECASE)

# Manual section numbering at the start of a heading title: "1.", "2)", "1.3.".
_NUMBERED_RE = re.compile(r"^\d+(\.\d+)*[.)]\s")

# Canonical first-line openers for a content page (case-sensitive).
_SKIMMER_OPENERS = (
    "This page",
    "This tutorial",
    "This guide",
    "This reference",
    "This how-to",
    "This explanation",
)

_DEFAULT_SECTIONS = ("tutorials", "how-to", "reference", "explanation")
_DEFAULT_KNOWN_TOP_LEVEL = (
    "index.md",
    "RULES.md",
    "reference/configuration.md",
    "reference/rules-index.md",
    "reference/cli.md",
)
_DEFAULT_RASTERS = ("png", "jpg", "jpeg", "gif", "webp", "bmp")


@dataclass(frozen=True)
class _Heading:
    """One heading parsed from a page, outside fenced code."""

    level: int
    text: str
    line: int


def _str_list(*, value: object, fallback: tuple[str, ...]) -> tuple[str, ...]:
    """Normalise a config value to a tuple of strings, or keep the fallback."""
    if isinstance(value, list):
        items = tuple(str(item) for item in value)
        return items if items else fallback
    return fallback


def _parse_headings(*, lines: list[str]) -> list[_Heading]:
    """Collect headings (ATX and setext) outside fenced code blocks.

    A setext heading is a non-blank text line immediately underlined by a run of
    ``=`` (level 1) or ``-`` (level 2). The underline is only honoured when the
    line above is prose, so a horizontal rule under a blank line is not a heading.
    """
    headings: list[_Heading] = []
    in_fence = False
    previous = ""
    for index, raw in enumerate(lines):
        stripped = raw.lstrip()
        if stripped.startswith("```") or stripped.startswith("~~~"):
            in_fence = not in_fence
            previous = ""
            continue
        if in_fence:
            previous = raw
            continue
        atx = _ATX_RE.match(raw)
        if atx is not None:
            headings.append(
                _Heading(level=len(atx.group(1)), text=atx.group(2).strip(), line=index + 1)
            )
            previous = raw
            continue
        if previous.strip() and not _ATX_RE.match(previous):
            if _SETEXT_H1_RE.match(raw):
                headings.append(_Heading(level=1, text=previous.strip(), line=index))
            elif _SETEXT_H2_RE.match(raw):
                headings.append(_Heading(level=2, text=previous.strip(), line=index))
        previous = raw
    return headings


def _v(*, file: str, line: int, rule: str, message: str, fix: str) -> Violation:
    """Build a Violation (one shape, since every docs finding is page-anchored)."""
    return Violation(file=file, line=line, rule=rule, message=message, fix=fix)


def _h1_finding(*, headings: list[_Heading], file: str) -> Violation | None:
    """DOCS-001: a content page must have exactly one level-1 heading."""
    h1s = [head for head in headings if head.level == 1]
    if len(h1s) == 1:
        return None
    if not h1s:
        return _v(
            file=file,
            line=1,
            rule="DOCS-001",
            message="Page has no level-1 heading",
            fix="Add a single '# Title' as the page's one H1",
        )
    return _v(
        file=file,
        line=h1s[1].line,
        rule="DOCS-001",
        message=f"Page has {len(h1s)} level-1 headings (expected exactly one)",
        fix="Keep one '# Title' and demote the others to '##' or lower",
    )


def _skip_finding(*, headings: list[_Heading], file: str) -> Violation | None:
    """DOCS-002: a heading may not jump more than one level below the previous."""
    previous_level = 0
    for head in headings:
        if previous_level and head.level > previous_level + 1:
            return _v(
                file=file,
                line=head.line,
                rule="DOCS-002",
                message=(
                    f"Heading level jumps from H{previous_level} to H{head.level} "
                    f"(skips H{previous_level + 1})"
                ),
                fix=f"Use an H{previous_level + 1} here, or promote the parent heading",
            )
        previous_level = head.level
    return None


def _numbered_findings(*, headings: list[_Heading], file: str) -> list[Violation]:
    """DOCS-008: an H2-H6 heading must not start with manual numbering."""
    found: list[Violation] = []
    for head in headings:
        if head.level >= 2 and _NUMBERED_RE.match(head.text):
            found.append(
                _v(
                    file=file,
                    line=head.line,
                    rule="DOCS-008",
                    message=f"Heading '{head.text}' starts with manual numbering",
                    fix="Drop the leading number; renderers number sections for you",
                )
            )
    return found


def _skimmer_finding(*, lines: list[str], headings: list[_Heading], file: str) -> Violation | None:
    """DOCS-003: a content page's first prose line opens with a canonical phrase.

    Exempt when the page has no single H1 (DOCS-001 owns that). The skimmer line
    is the first non-blank line after the H1; it must begin with one of the
    canonical openers, so a reader knows in one glance what the page is for.
    """
    h1s = [head for head in headings if head.level == 1]
    if len(h1s) != 1:
        return None
    opener = _first_prose_line(lines=lines, after_line=h1s[0].line)
    if opener is not None and opener.startswith(_SKIMMER_OPENERS):
        return None
    detail = "is missing" if opener is None else "does not start with a canonical opener"
    return _v(
        file=file,
        line=h1s[0].line,
        rule="DOCS-003",
        message=f"Content page's first paragraph {detail}",
        fix="Open with 'This page', 'This tutorial', 'This guide', and so on",
    )


def _first_prose_line(*, lines: list[str], after_line: int) -> str | None:
    """First non-blank line after a 1-based heading line, skipping code fences."""
    in_fence = False
    for raw in lines[after_line:]:
        stripped = raw.strip()
        if stripped.startswith("```") or stripped.startswith("~~~"):
            in_fence = not in_fence
            continue
        if in_fence or not stripped:
            continue
        return stripped
    return None


def _missing_alt(*, attributes: str) -> bool:
    """True when an <img> attribute string has no alt, or an empty alt."""
    match = _ALT_ATTR_RE.search(attributes)
    if match is None:
        return True
    return not (match.group(2) or match.group(3) or "").strip()


def _image_findings(*, lines: list[str], file: str) -> list[Violation]:
    """DOCS-004: every Markdown image and <img> tag carries non-empty alt text."""
    found: list[Violation] = []
    in_fence = False
    for index, raw in enumerate(lines):
        stripped = raw.lstrip()
        if stripped.startswith("```") or stripped.startswith("~~~"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        for match in _MD_IMAGE_RE.finditer(raw):
            if not match.group(1).strip():
                found.append(_image_alt_violation(file=file, line=index + 1))
        for match in _IMG_TAG_RE.finditer(raw):
            if _missing_alt(attributes=match.group(1)):
                found.append(_image_alt_violation(file=file, line=index + 1))
    return found


def _image_alt_violation(*, file: str, line: int) -> Violation:
    return _v(
        file=file,
        line=line,
        rule="DOCS-004",
        message="Image has no alternative text",
        fix="Add descriptive alt text: '![a labelled diagram](...)' or alt=\"...\"",
    )


def _is_local_raster(*, target: str, rasters: tuple[str, ...]) -> bool:
    """True when a reference is a local path whose extension is a raster format."""
    if _SCHEME_RE.match(target):
        return False
    suffix = Path(target.split("#", 1)[0].split("?", 1)[0]).suffix.lstrip(".").lower()
    return suffix in rasters


def _allowed(*, target: str, allow: tuple[str, ...]) -> bool:
    """True when an image target matches any allow glob (exempt from prefer-svg)."""
    clean = target.split("#", 1)[0].split("?", 1)[0]
    return any(fnmatch.fnmatch(clean, pattern) for pattern in allow)


def _raster_findings(
    *, lines: list[str], file: str, rasters: tuple[str, ...], allow: tuple[str, ...]
) -> list[Violation]:
    """DOCS-005: a local raster image should be an SVG or a Mermaid diagram."""
    found: list[Violation] = []
    in_fence = False
    for index, raw in enumerate(lines):
        stripped = raw.lstrip()
        if stripped.startswith("```") or stripped.startswith("~~~"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        for match in _MD_IMAGE_RE.finditer(raw):
            target = match.group(2)
            if _is_local_raster(target=target, rasters=rasters) and not _allowed(
                target=target, allow=allow
            ):
                found.append(
                    _v(
                        file=file,
                        line=index + 1,
                        rule="DOCS-005",
                        message=f"Local raster image '{target}' (prefer a vector format)",
                        fix="Export the diagram to SVG, or draw it inline with Mermaid",
                    )
                )
    return found


@dataclass
class DocsCheck:
    """Opt-in, tree-scoped structure and accessibility for a Markdown docs tree."""

    name: str = "docs"
    description: str = "Markdown docs structure and accessibility (Diataxis sections)"
    enabled: bool = False
    scope: str = "tree"  # inspects the docs tree, including directory structure
    is_tree_scoped: bool = True
    docs_root: str = "docs"
    sections: tuple[str, ...] = _DEFAULT_SECTIONS
    known_top_level: tuple[str, ...] = _DEFAULT_KNOWN_TOP_LEVEL
    raster_extensions: tuple[str, ...] = _DEFAULT_RASTERS
    allow: tuple[str, ...] = ()
    rules: list[str] = field(
        default_factory=lambda: [
            "DOCS-001: A content page has exactly one level-1 heading",
            "DOCS-002: Heading levels descend one step at a time",
            "DOCS-003: A content page opens with a canonical skimmer line",
            "DOCS-004: Every image carries alternative text",
            "DOCS-005: Prefer SVG or Mermaid over a local raster image",
            "DOCS-006: A known section directory carries an index page",
            "DOCS-007: Every page has a home in the architecture",
            "DOCS-008: Headings are not numbered by hand",
        ]
    )

    def configure(self, *, settings: dict[str, object]) -> None:
        """Apply ``[tool.lanorme.docs]`` configuration."""
        if "enabled" in settings:
            self.enabled = bool(settings["enabled"])
        if isinstance(settings.get("docs_root"), str):
            self.docs_root = str(settings["docs_root"])
        self.sections = _str_list(value=settings.get("sections"), fallback=self.sections)
        self.known_top_level = _str_list(
            value=settings.get("known_top_level"), fallback=self.known_top_level
        )
        self.raster_extensions = tuple(
            ext.lower()
            for ext in _str_list(
                value=settings.get("raster_extensions"), fallback=self.raster_extensions
            )
        )
        self.allow = _str_list(value=settings.get("allow"), fallback=self.allow)

    def _page_findings(
        self, *, lines: list[str], file: str, is_content: bool
    ) -> tuple[list[Violation], list[Violation]]:
        """Per-page violations and warnings (everything except tree-level rules)."""
        headings = _parse_headings(lines=lines)
        violations: list[Violation] = []
        for finding in (
            _h1_finding(headings=headings, file=file),
            _skip_finding(headings=headings, file=file),
        ):
            if finding is not None:
                violations.append(finding)
        if is_content:
            skimmer = _skimmer_finding(lines=lines, headings=headings, file=file)
            if skimmer is not None:
                violations.append(skimmer)
        violations.extend(_image_findings(lines=lines, file=file))

        warnings = _numbered_findings(headings=headings, file=file)
        warnings.extend(
            _raster_findings(
                lines=lines,
                file=file,
                rasters=self.raster_extensions,
                allow=self.allow,
            )
        )
        return violations, warnings

    def _quadrant_finding(self, *, file: str, rel_posix: str) -> Violation | None:
        """DOCS-007: a page outside a known section and not a known top-level page."""
        top = rel_posix.split("/", 1)[0]
        if top in self.sections and "/" in rel_posix:
            return None
        if rel_posix in self.known_top_level:
            return None
        return _v(
            file=file,
            line=1,
            rule="DOCS-007",
            message=f"Page '{rel_posix}' is not in a known section or a known top-level page",
            fix="Move it under a Diataxis section, or list it in known_top_level",
        )

    def _section_index_findings(self, *, docs_dir: Path, pages: list[Path]) -> list[Violation]:
        """DOCS-006: a known section directory with pages but no index.md."""
        found: list[Violation] = []
        relatives = {page.relative_to(docs_dir).as_posix() for page in pages}
        for section in self.sections:
            prefix = f"{section}/"
            in_section = [rel for rel in relatives if rel.startswith(prefix)]
            if in_section and f"{section}/index.md" not in relatives:
                found.append(
                    _v(
                        file=f"{self.docs_root}/{section}/",
                        line=1,
                        rule="DOCS-006",
                        message=f"Section '{section}' has pages but no index.md",
                        fix=f"Add {self.docs_root}/{section}/index.md as the section landing page",
                    )
                )
        return found

    def run(self, *, src_root: str) -> CheckResult:
        if not self.enabled:
            return CheckResult(check=self.name, status=Status.PASS)

        root = Path(src_root)
        docs_dir = root / self.docs_root
        violations: list[Violation] = []
        warnings: list[Violation] = []
        pages: list[Path] = []

        for path in iter_files(docs_dir, suffix=".md"):
            if not path.is_file() or any(part in _SKIP_PARTS for part in path.parts):
                continue
            pages.append(path)
            rel_posix = path.relative_to(docs_dir).as_posix()
            file = str(path.relative_to(root))
            try:
                lines = path.read_text(encoding="utf-8").splitlines()
            except (OSError, UnicodeDecodeError):
                continue
            page_violations, page_warnings = self._page_findings(
                lines=lines,
                file=file,
                is_content=path.name != "index.md",
            )
            violations.extend(page_violations)
            warnings.extend(page_warnings)
            quadrant = self._quadrant_finding(file=file, rel_posix=rel_posix)
            if quadrant is not None:
                warnings.append(quadrant)

        warnings.extend(self._section_index_findings(docs_dir=docs_dir, pages=pages))

        status = Status.FAIL if violations else (Status.WARN if warnings else Status.PASS)
        return CheckResult(check=self.name, status=status, violations=violations, warnings=warnings)


register(DocsCheck())
