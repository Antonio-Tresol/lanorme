"""STALE-001: Stale path references in Python docstrings and comments.

When a project moves or renames a directory, references to the old path tend to
linger in docstrings and comments long after the code has moved. This check
flags any configured stale path token (matched both backtick-wrapped and as a
plain ``old/file.py`` reference) so the regressions get caught mechanically.

Configure the stale tokens in ``[tool.lanorme.stale_paths]``::

    [tool.lanorme.stale_paths]
    tokens = ["src/", "old_pkg/"]

With no configuration the check is inert (always PASS).

Boundary exemptions: files under ``tests/`` are skipped (fixtures legitimately
reference legacy layouts).

Run:
    lanorme check . --check=stale_paths
"""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass, field
from pathlib import Path

from lanorme import CheckResult, Status, Violation, register

# Default is empty → the check is inert until configured.
_STALE_TOKENS: tuple[str, ...] = ()
_EXEMPT_PATH_FRAGMENTS = ("tests/",)


def _compile_patterns(tokens: tuple[str, ...]) -> list[re.Pattern[str]]:
    """Build backtick-wrapped and plain-path matchers for each stale token."""
    patterns: list[re.Pattern[str]] = []
    for token in tokens:
        escaped = re.escape(token)
        patterns.append(re.compile(rf"`{escaped}[A-Za-z0-9_./<>-]*`"))
        patterns.append(re.compile(rf"\b{escaped}[A-Za-z0-9_]+\.py\b"))
    return patterns


def _is_exempt(*, relative_path: str) -> bool:
    normalised = relative_path.replace("\\", "/")
    return any(normalised.startswith(p) for p in _EXEMPT_PATH_FRAGMENTS)


def _scan_text(
    *,
    text: str,
    line_offset: int,
    relative_file: str,
    patterns: list[re.Pattern[str]],
) -> list[Violation]:
    findings: list[Violation] = []
    for lineno_0, line in enumerate(text.splitlines()):
        for pattern in patterns:
            for match in pattern.finditer(line):
                findings.append(
                    Violation(
                        file=relative_file,
                        line=line_offset + lineno_0,
                        rule="STALE-001",
                        message=f"Stale path reference '{match.group(0)}'",
                        fix=f"Update '{match.group(0)}' to the current path",
                    )
                )
    return findings


def _scan_file(
    *,
    py_file: Path,
    relative_file: str,
    patterns: list[re.Pattern[str]],
) -> list[Violation]:
    try:
        source = py_file.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(py_file))
    except (OSError, UnicodeDecodeError, SyntaxError):
        return []

    violations: list[Violation] = []

    # Inline comments.
    for lineno_0, line in enumerate(source.splitlines()):
        comment_idx = line.find("#")
        if comment_idx == -1:
            continue
        comment_text = line[comment_idx:]
        for pattern in patterns:
            for match in pattern.finditer(comment_text):
                violations.append(
                    Violation(
                        file=relative_file,
                        line=lineno_0 + 1,
                        rule="STALE-001",
                        message=f"Stale path reference '{match.group(0)}' in comment",
                        fix=f"Update '{match.group(0)}' to the current path",
                    )
                )

    # Docstrings, module, class, function.
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Module | ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef)
            and node.body
            and isinstance(node.body[0], ast.Expr)
            and isinstance(node.body[0].value, ast.Constant)
            and isinstance(node.body[0].value.value, str)
        ):
            const = node.body[0].value
            violations.extend(
                _scan_text(
                    text=const.value,
                    line_offset=const.lineno,
                    relative_file=relative_file,
                    patterns=patterns,
                )
            )

    return violations


@dataclass
class StalePathsCheck:
    """Catches stale path references in Python docstrings and comments."""

    name: str = "stale_paths"
    description: str = "Stale path references (old directory tokens) in Python source"
    tokens: tuple[str, ...] = _STALE_TOKENS
    rules: list[str] = field(
        default_factory=lambda: [
            "STALE-001: No references to configured stale path tokens in docstrings or comments",
        ]
    )

    def configure(self, *, settings: dict[str, list[str]]) -> None:
        """Apply ``[tool.lanorme.stale_paths]`` configuration."""
        self.tokens = tuple(settings.get("tokens", []))

    def run(self, *, src_root: str) -> CheckResult:
        violations: list[Violation] = []
        patterns = _compile_patterns(self.tokens)
        if not patterns:
            return CheckResult(check=self.name, status=Status.PASS, violations=[])

        src_path = Path(src_root)
        for py_file in sorted(src_path.rglob("*.py")):
            relative_file = str(py_file.relative_to(src_path))
            if _is_exempt(relative_path=relative_file):
                continue
            violations.extend(
                _scan_file(py_file=py_file, relative_file=relative_file, patterns=patterns)
            )

        status = Status.FAIL if violations else Status.PASS
        return CheckResult(check=self.name, status=status, violations=violations)


register(StalePathsCheck())
