"""IMPORT-001 and ENDPOINT-001: Pattern divergence detection.

Rules:
    IMPORT-001    No inline imports inside functions, all imports at module level
    ENDPOINT-001  Endpoint functions should not exceed nesting depth of 4 (warning)

The earlier TYPING-001 (no ``if TYPE_CHECKING:`` outside model files) was
dropped on 2026-05-26: the multi-reviewer audit found that the rule inverted
the community typing consensus (ruff's TCH family actively *promotes*
``TYPE_CHECKING`` guards to keep runtime import graphs lean). It can come back
later as an explicit opt-in with the premise inverted (encourage, not forbid).

Run:
    lanorme check . --check=pattern_divergence
"""

from __future__ import annotations

import ast
from dataclasses import dataclass, field
from pathlib import Path

from lanorme import CheckResult, Status, Violation, register

# ---------------------------------------------------------------------------
# IMPORT-001: No inline imports inside functions
# ---------------------------------------------------------------------------

# ORM models commonly live under infrastructure/repositories/; TYPE_CHECKING
# guards are tolerated there for ORM forward references.
_MODELS_DIR = "infrastructure/repositories"

# Directories where conditional inline imports are legitimate:
# - observability: OTel instrumentation packages loaded conditionally
# - main.py: app factory wires dependencies at startup
_PATTERN_001_EXEMPT_PATHS = (
    "infrastructure/observability/",
    "api/v1/main.py",
)


def _is_inside_function(*, node: ast.AST, parents: dict[int, ast.AST]) -> bool:
    """Walk up the parent chain to see if *node* is inside a function body."""
    current_id = id(node)
    while current_id in parents:
        parent = parents[current_id]
        if isinstance(parent, ast.FunctionDef | ast.AsyncFunctionDef):
            return True
        current_id = id(parent)
    return False


def _is_inside_type_checking_guard(
    *,
    node: ast.AST,
    parents: dict[int, ast.AST],
) -> bool:
    """Return True if *node* lives inside an ``if TYPE_CHECKING:`` block."""
    current_id = id(node)
    while current_id in parents:
        parent = parents[current_id]
        if isinstance(parent, ast.If):
            test = parent.test
            # Plain ``TYPE_CHECKING``
            if isinstance(test, ast.Name) and test.id == "TYPE_CHECKING":
                return True
            # ``typing.TYPE_CHECKING``
            if isinstance(test, ast.Attribute) and test.attr == "TYPE_CHECKING":
                return True
        current_id = id(parent)
    return False


def _build_parent_map(*, tree: ast.AST) -> dict[int, ast.AST]:
    """Build a child-id → parent mapping for the entire AST."""
    parents: dict[int, ast.AST] = {}
    for parent in ast.walk(tree):
        for child in ast.iter_child_nodes(parent):
            parents[id(child)] = parent
    return parents


def _line_has_noqa(*, source_lines: list[str], lineno: int, rule: str) -> bool:
    """Return True if the source line has a ``# noqa: <rule>`` comment."""
    if 1 <= lineno <= len(source_lines):
        line = source_lines[lineno - 1]
        if f"# noqa: {rule}" in line:
            return True
    return False


def _check_inline_imports(
    *,
    tree: ast.AST,
    source_lines: list[str],
    relative_file: str,
) -> list[Violation]:
    """IMPORT-001: Find import statements inside function bodies."""
    # Exempt paths where conditional imports are legitimate.
    normalized = relative_file.replace("\\", "/")
    for exempt in _PATTERN_001_EXEMPT_PATHS:
        if normalized.startswith(exempt) or normalized == exempt:
            return []

    violations: list[Violation] = []
    parents = _build_parent_map(tree=tree)

    for node in ast.walk(tree):
        if not isinstance(node, ast.Import | ast.ImportFrom):
            continue

        if not _is_inside_function(node=node, parents=parents):
            continue

        # Exempt imports inside TYPE_CHECKING guards (though discouraged).
        if _is_inside_type_checking_guard(node=node, parents=parents):
            continue

        if _line_has_noqa(
            source_lines=source_lines,
            lineno=node.lineno,
            rule="IMPORT-001",
        ):
            continue

        # Build a human-readable module name for the message.
        if isinstance(node, ast.ImportFrom):
            module_name = node.module or "<relative>"
        else:
            module_name = ", ".join(alias.name for alias in node.names)

        violations.append(
            Violation(
                file=relative_file,
                line=node.lineno,
                rule="IMPORT-001: No inline imports inside functions",
                message=f"Import '{module_name}' found inside a function body",
                fix="Move this import to the top of the file, at module level",
            ),
        )

    return violations


# ---------------------------------------------------------------------------
# (TYPING-001 was removed on 2026-05-26; see the module docstring.)
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# ENDPOINT-001: Endpoint functions should not exceed complexity threshold
# ---------------------------------------------------------------------------

_ENDPOINTS_DIR = "api/v1/endpoints"
_MAX_NESTING_DEPTH = 4

# AST node types that introduce a new nesting level.
_NESTING_NODES = (
    ast.If,
    ast.For,
    ast.AsyncFor,
    ast.While,
    ast.With,
    ast.AsyncWith,
    ast.Try,
    ast.ExceptHandler,
)


def _max_nesting_depth(*, node: ast.AST, depth: int = 0) -> int:
    """Recursively compute the maximum nesting depth of control-flow nodes."""
    max_depth = depth

    for child in ast.iter_child_nodes(node):
        if isinstance(child, _NESTING_NODES):
            child_depth = _max_nesting_depth(node=child, depth=depth + 1)
        else:
            child_depth = _max_nesting_depth(node=child, depth=depth)
        max_depth = max(max_depth, child_depth)

    return max_depth


def _check_endpoint_nesting(
    *,
    tree: ast.AST,
    source_lines: list[str],
    relative_file: str,
) -> list[Violation]:
    """ENDPOINT-001: Flag endpoint functions with nesting > 4 levels."""
    normalized = relative_file.replace("\\", "/")
    if not normalized.startswith(_ENDPOINTS_DIR):
        return []

    warnings: list[Violation] = []

    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            continue

        depth = _max_nesting_depth(node=node)
        if depth <= _MAX_NESTING_DEPTH:
            continue

        if _line_has_noqa(
            source_lines=source_lines,
            lineno=node.lineno,
            rule="ENDPOINT-001",
        ):
            continue

        warnings.append(
            Violation(
                file=relative_file,
                line=node.lineno,
                rule="ENDPOINT-001: Endpoint nesting depth exceeds threshold (warning)",
                message=(
                    f"Function '{node.name}' has nesting depth {depth} "
                    f"(max {_MAX_NESTING_DEPTH}) — consider extracting helper functions"
                ),
                fix=(
                    "Extract deeply nested logic into private helper functions "
                    "or service methods to reduce cognitive complexity"
                ),
            ),
        )

    return warnings


# ---------------------------------------------------------------------------
# Check class + registration
# ---------------------------------------------------------------------------


@dataclass
class PatternDivergenceCheck:
    """Detects pattern divergence: inline imports and over-nested endpoint functions."""

    name: str = "pattern_divergence"
    description: str = (
        "Pattern divergence detection (inline imports, TYPE_CHECKING, endpoint consistency)"
    )
    rules: list[str] = field(
        default_factory=lambda: [
            "IMPORT-001: No inline imports inside functions",
            "ENDPOINT-001: Endpoint nesting depth exceeds threshold (warning)",
        ],
    )

    def run(self, *, src_root: str) -> CheckResult:
        """Scan Python files under src/ for pattern divergence."""
        violations: list[Violation] = []
        warnings: list[Violation] = []
        src_path = Path(src_root)

        for py_file in sorted(src_path.rglob("*.py")):
            relative_file = str(py_file.relative_to(src_path))

            # Skip test files.
            if Path(relative_file).name.startswith("test_"):
                continue

            try:
                source = py_file.read_text(encoding="utf-8")
                tree = ast.parse(source, filename=str(py_file))
            except (OSError, UnicodeDecodeError, SyntaxError):
                warnings.append(
                    Violation(
                        file=relative_file,
                        line=0,
                        rule="PATTERN-000: parse error",
                        message=f"Could not parse {py_file.name} — skipping",
                        fix="Fix the syntax error first",
                    ),
                )
                continue

            source_lines = source.splitlines()

            # IMPORT-001: inline imports (violation)
            violations.extend(
                _check_inline_imports(
                    tree=tree,
                    source_lines=source_lines,
                    relative_file=relative_file,
                ),
            )

            # ENDPOINT-001: endpoint nesting depth (warning)
            warnings.extend(
                _check_endpoint_nesting(
                    tree=tree,
                    source_lines=source_lines,
                    relative_file=relative_file,
                ),
            )

        status = Status.FAIL if violations else (Status.WARN if warnings else Status.PASS)
        return CheckResult(
            check=self.name,
            status=status,
            violations=violations,
            warnings=warnings,
        )


# Self-register on import.
register(PatternDivergenceCheck())
