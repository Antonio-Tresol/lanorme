"""ART-001 / ART-002: Stray artifact detection.

Flags files that tend to accumulate as clutter, screenshots, scratch scripts,
editor backups, OS junk, build leftovers, and stray images/binaries dropped
outside an asset directory. The goal is to surface them in a normal
``lanorme check`` run so they get deleted (or deliberately allowlisted) rather
than quietly polluting the tree, whether or not they are tracked by git.

Rules:
    ART-001  A file matches a scratch/temp/OS/build junk pattern
             (``screenshot*``, ``*~``, ``*.bak``, ``.DS_Store``, ``*.pyc`` …).
    ART-002  An image/binary file sits outside any asset directory
             (``docs/``, ``assets/``, ``static/`` …).

This check is on by default with conservative patterns. Tune it in
``[tool.lanorme.stray_artifacts]``::

    [tool.lanorme.stray_artifacts]
    patterns   = ["*.heic"]            # extra name globs flagged as ART-001
    extensions = [".zip", ".pdf"]      # extra extensions flagged as ART-002
    assets     = ["screenshots"]       # extra dirs where binaries are allowed
    allow      = ["docs/diagram.png"]  # globs (path or name) never flagged
    exclude    = ["sandbox"]           # extra directories to skip entirely

Run:
    lanorme check . --check=stray_artifacts
"""

from __future__ import annotations

import fnmatch
import os
from dataclasses import dataclass, field
from pathlib import Path

from lanorme import CheckResult, Status, Violation, register

# Directories never scanned (vendored / generated / VCS).
_VENDOR_DIRS = frozenset(
    {
        ".git",
        ".hg",
        ".svn",
        ".venv",
        "venv",
        "node_modules",
        "__pycache__",
        ".ruff_cache",
        ".pytest_cache",
        ".mypy_cache",
        ".tox",
        ".eggs",
        "dist",
        "build",
    }
)

# Directories where images/binaries are expected and therefore not ART-002.
_DEFAULT_ASSET_DIRS = ("assets", "static", "images", "img", "media", "public", "docs", ".github")

# Name globs that are almost always clutter (ART-001), matched on the basename.
_DEFAULT_NAME_GLOBS = (
    "screenshot*",
    "Screenshot*",
    "Screen Shot*",
    "screen shot*",
    "*~",
    "*.bak",
    "*.orig",
    "*.rej",
    "*.swp",
    "*.swo",
    "*.tmp",
    "scratch*",
    "Scratch*",
    "untitled*",
    "Untitled*",
    "tmp.*",
    "temp.*",
    "*.pyc",
    "*.pyo",
    ".coverage",
    "coverage.xml",
    ".DS_Store",
    "Thumbs.db",
    "desktop.ini",
    "nohup.out",
    "core.*",
)

# Image/binary extensions flagged (ART-002) when outside an asset directory.
_DEFAULT_BINARY_EXTS = (".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp")


def _matches_any(*, name: str, globs: tuple[str, ...]) -> bool:
    return any(fnmatch.fnmatch(name, glob) for glob in globs)


@dataclass
class StrayArtifactsCheck:
    """Flags stray clutter files (screenshots, scratch, OS junk, stray binaries)."""

    name: str = "stray_artifacts"
    description: str = "Stray artifact detection (screenshots, scratch files, OS junk)"
    extra_patterns: tuple[str, ...] = ()
    extra_extensions: tuple[str, ...] = ()
    allow: tuple[str, ...] = ()
    extra_excludes: tuple[str, ...] = ()
    asset_dirs: tuple[str, ...] = _DEFAULT_ASSET_DIRS
    rules: list[str] = field(
        default_factory=lambda: [
            "ART-001: Scratch/temp/screenshot/OS/build artifacts must not pollute the tree",
            "ART-002: Images/binaries outside an asset directory are flagged as stray",
        ]
    )

    def configure(self, *, settings: dict[str, list[str]]) -> None:
        """Apply ``[tool.lanorme.stray_artifacts]`` configuration."""
        self.extra_patterns = tuple(settings.get("patterns", []))
        self.extra_extensions = tuple(e.lower() for e in settings.get("extensions", []))
        self.allow = tuple(settings.get("allow", []))
        self.extra_excludes = tuple(settings.get("exclude", []))
        if "assets" in settings:
            self.asset_dirs = (*_DEFAULT_ASSET_DIRS, *settings["assets"])

    def _classify(self, *, rel: Path) -> str | None:
        """Return the rule code a file violates, or None if it is fine."""
        rel_posix = rel.as_posix()
        if any(
            fnmatch.fnmatch(rel_posix, pat) or fnmatch.fnmatch(rel.name, pat) for pat in self.allow
        ):
            return None

        if _matches_any(name=rel.name, globs=_DEFAULT_NAME_GLOBS + self.extra_patterns):
            return "ART-001"

        if any(part in self.asset_dirs for part in rel.parts[:-1]):
            return None

        if rel.suffix.lower() in (*_DEFAULT_BINARY_EXTS, *self.extra_extensions):
            return "ART-002"

        return None

    def run(self, *, src_root: str) -> CheckResult:
        violations: list[Violation] = []
        root = Path(src_root)
        skip = _VENDOR_DIRS | set(self.extra_excludes)

        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in skip]
            for filename in filenames:
                rel = (Path(dirpath) / filename).relative_to(root)
                code = self._classify(rel=rel)
                if code is None:
                    continue
                violations.append(_build_violation(code=code, rel=rel))

        status = Status.FAIL if violations else Status.PASS
        return CheckResult(check=self.name, status=status, violations=violations)


def _build_violation(*, code: str, rel: Path) -> Violation:
    if code == "ART-001":
        message = f"Stray artifact '{rel.as_posix()}' matches a scratch/temp/OS-junk pattern"
    else:
        message = f"Stray image/binary '{rel.as_posix()}' sits outside an asset directory"
    return Violation(
        file=rel.as_posix(),
        line=0,
        rule=code,
        message=message,
        fix=(
            "Delete the file, or — if intentional — add it to "
            "[tool.lanorme.stray_artifacts] allow/assets/exclude"
        ),
    )


register(StrayArtifactsCheck())
