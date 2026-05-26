"""SIZE-001 through SIZE-005: File size, function length, complexity, and parameter enforcement.

Checks:
    SIZE-001  Python files warn at 300 effective lines, error at 500
    SIZE-002  Functions/methods warn at 50 lines, error at 80
    SIZE-003  Classes with >10 methods are a warning (decomposition candidate)
    SIZE-004  Cyclomatic complexity warn at 10, error at 15
    SIZE-005  Parameter count warn at 5, error at 8 (excluding self/cls)

Effective lines = non-blank, non-comment lines.

Excludes: __init__.py, conftest.py, alembic/, migrations/, test_* prefixed files.

Run:
    lanorme check . --check=file_limits
"""

from __future__ import annotations

import ast
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from lanorme import CheckResult, Status, Violation, register

# SIZE-001 thresholds (effective lines per file).
FILE_WARN_LINES = 300
FILE_ERROR_LINES = 500

# SIZE-002 thresholds (lines per function/method).
FUNC_WARN_LINES = 50
FUNC_ERROR_LINES = 80

# SIZE-003 threshold (methods per class).
CLASS_METHOD_WARN = 10

# SIZE-004 thresholds (cyclomatic complexity per function).
COMPLEXITY_WARN = 10
COMPLEXITY_ERROR = 15

# SIZE-005 thresholds (parameters per function, excluding self/cls).
PARAM_WARN = 5
PARAM_ERROR = 8

# Files and directories excluded from scanning.
EXCLUDED_FILENAMES = {"__init__.py", "conftest.py"}
EXCLUDED_DIR_PARTS = {"alembic", "migrations"}


def _should_exclude(*, file_path: Path) -> bool:
    """Determine whether a file should be skipped based on exclusion rules."""
    if file_path.name in EXCLUDED_FILENAMES:
        return True
    if file_path.name.startswith("test_"):
        return True
    return any(part in EXCLUDED_DIR_PARTS for part in file_path.parts)


def _count_effective_lines(*, source: str) -> int:
    """Count non-blank, non-comment-only lines in source code."""
    count = 0
    for line in source.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("#"):
            continue
        count += 1
    return count


def _check_file_size(
    *,
    source: str,
    relative_file: str,
) -> tuple[list[Violation], list[Violation]]:
    """SIZE-001: Warn at 300 effective lines, error at 500."""
    violations: list[Violation] = []
    warnings: list[Violation] = []
    effective = _count_effective_lines(source=source)

    if effective >= FILE_ERROR_LINES:
        violations.append(
            Violation(
                file=relative_file,
                line=1,
                rule="SIZE-001: File exceeds 500 effective lines",
                message=f"File has {effective} effective lines (limit: {FILE_ERROR_LINES})",
                fix="Split into smaller modules with focused responsibilities",
            ),
        )
    elif effective >= FILE_WARN_LINES:
        warnings.append(
            Violation(
                file=relative_file,
                line=1,
                rule="SIZE-001: File approaching 500 effective lines",
                message=f"File has {effective} effective lines (warn: {FILE_WARN_LINES})",
                fix="Consider splitting into smaller modules before it grows further",
            ),
        )

    return violations, warnings


def _check_function_lengths(
    *,
    tree: ast.AST,
    relative_file: str,
) -> tuple[list[Violation], list[Violation]]:
    """SIZE-002: Warn at 50 lines per function, error at 80."""
    violations: list[Violation] = []
    warnings: list[Violation] = []

    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            continue

        if node.end_lineno is None:
            continue

        length = node.end_lineno - node.lineno + 1

        if length >= FUNC_ERROR_LINES:
            violations.append(
                Violation(
                    file=relative_file,
                    line=node.lineno,
                    rule="SIZE-002: Function exceeds 80 lines",
                    message=f"Function '{node.name}' is {length} lines (limit: {FUNC_ERROR_LINES})",
                    fix="Extract helper functions or simplify control flow",
                ),
            )
        elif length >= FUNC_WARN_LINES:
            warnings.append(
                Violation(
                    file=relative_file,
                    line=node.lineno,
                    rule="SIZE-002: Function approaching 80 lines",
                    message=f"Function '{node.name}' is {length} lines (warn: {FUNC_WARN_LINES})",
                    fix="Consider extracting helper functions before it grows further",
                ),
            )

    return violations, warnings


def _check_class_method_count(
    *,
    tree: ast.AST,
    relative_file: str,
) -> list[Violation]:
    """SIZE-003: Classes with >10 methods are candidates for decomposition."""
    warnings: list[Violation] = []

    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue

        method_count = sum(
            1 for child in node.body if isinstance(child, ast.FunctionDef | ast.AsyncFunctionDef)
        )

        if method_count > CLASS_METHOD_WARN:
            warnings.append(
                Violation(
                    file=relative_file,
                    line=node.lineno,
                    rule="SIZE-003: Class has too many methods",
                    message=f"Class '{node.name}' has {method_count} methods (warn: {CLASS_METHOD_WARN})",
                    fix="Consider decomposing into smaller, focused classes",
                ),
            )

    return warnings


def _cyclomatic_complexity(*, func_node: ast.FunctionDef | ast.AsyncFunctionDef) -> int:
    """Calculate cyclomatic complexity for a single function.

    Walks only direct descendants, nested function bodies are excluded.
    Base complexity is 1. Increments for branching/looping constructs and
    each extra boolean operand in BoolOp nodes.
    """
    complexity = 1
    _BRANCHING_TYPES = (
        ast.If,
        ast.IfExp,
        ast.For,
        ast.While,
        ast.ExceptHandler,
        ast.With,
        ast.Assert,
    )

    # Walk the function body but skip nested function definitions.
    nodes_to_visit: list[ast.AST] = list(func_node.body)
    while nodes_to_visit:
        node = nodes_to_visit.pop()
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            continue
        if isinstance(node, _BRANCHING_TYPES):
            complexity += 1
        elif isinstance(node, ast.BoolOp):
            complexity += len(node.values) - 1
        nodes_to_visit.extend(ast.iter_child_nodes(node))

    return complexity


@dataclass(frozen=True)
class _MetricSpec:
    """Thresholds and messaging for one per-function numeric metric."""

    metric: Callable[..., int]
    warn: int
    error: int
    error_rule: str
    warn_rule: str
    noun: str
    fix_error: str
    fix_warn: str


def _check_function_metric(
    *,
    tree: ast.AST,
    relative_file: str,
    spec: _MetricSpec,
) -> tuple[list[Violation], list[Violation]]:
    """Apply a metric to every function and bucket the result into warn/error."""
    violations: list[Violation] = []
    warnings: list[Violation] = []

    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            continue

        value = spec.metric(func_node=node)

        if value >= spec.error:
            violations.append(
                Violation(
                    file=relative_file,
                    line=node.lineno,
                    rule=spec.error_rule,
                    message=f"Function '{node.name}' has {spec.noun} {value} (limit: {spec.error})",
                    fix=spec.fix_error,
                ),
            )
        elif value >= spec.warn:
            warnings.append(
                Violation(
                    file=relative_file,
                    line=node.lineno,
                    rule=spec.warn_rule,
                    message=f"Function '{node.name}' has {spec.noun} {value} (warn: {spec.warn})",
                    fix=spec.fix_warn,
                ),
            )

    return violations, warnings


def _count_parameters(*, func_node: ast.FunctionDef | ast.AsyncFunctionDef) -> int:
    """Count function parameters, excluding self and cls."""
    params = func_node.args.posonlyargs + func_node.args.args + func_node.args.kwonlyargs
    count = len(params)

    # Exclude self/cls (first positional arg in methods).
    if params and params[0].arg in ("self", "cls"):
        count -= 1

    # Count *args and **kwargs if present.
    if func_node.args.vararg:
        count += 1
    if func_node.args.kwarg:
        count += 1

    return count


_COMPLEXITY_SPEC = _MetricSpec(
    metric=_cyclomatic_complexity,
    warn=COMPLEXITY_WARN,
    error=COMPLEXITY_ERROR,
    error_rule="SIZE-004: Function exceeds complexity 15",
    warn_rule="SIZE-004: Function approaching complexity 15",
    noun="cyclomatic complexity",
    fix_error="Extract helper functions or simplify branching logic",
    fix_warn="Consider simplifying branching logic before it grows further",
)

_PARAM_SPEC = _MetricSpec(
    metric=_count_parameters,
    warn=PARAM_WARN,
    error=PARAM_ERROR,
    error_rule="SIZE-005: Function exceeds 8 parameters",
    warn_rule="SIZE-005: Function approaching 8 parameters",
    noun="parameter count",
    fix_error="Group related parameters into a dataclass or TypedDict",
    fix_warn="Consider grouping related parameters into a dataclass or TypedDict",
)


@dataclass
class FileLimitsCheck:
    """Enforces file size and function length limits."""

    name: str = "file_limits"
    description: str = "File size, function length, complexity, and parameter enforcement"
    rules: list[str] = field(
        default_factory=lambda: [
            "SIZE-001: Python files warn at 300 effective lines, error at 500",
            "SIZE-002: Functions/methods warn at 50 lines, error at 80",
            "SIZE-003: Classes with >10 methods are a warning",
            "SIZE-004: Cyclomatic complexity warn at 10, error at 15",
            "SIZE-005: Parameter count warn at 5, error at 8 (excluding self/cls)",
        ],
    )

    def run(self, *, src_root: str) -> CheckResult:
        """Scan all Python files under src/ and enforce size limits."""
        violations: list[Violation] = []
        warnings: list[Violation] = []
        src_path = Path(src_root)

        for py_file in sorted(src_path.rglob("*.py")):
            if _should_exclude(file_path=py_file):
                continue

            relative_file = str(py_file.relative_to(src_path))

            try:
                source = py_file.read_text(encoding="utf-8")
                tree = ast.parse(source, filename=str(py_file))
            except (OSError, UnicodeDecodeError, SyntaxError):
                warnings.append(
                    Violation(
                        file=relative_file,
                        line=0,
                        rule="SIZE-000: parse error",
                        message=f"Could not parse {py_file.name} — skipping",
                        fix="Fix the syntax error first",
                    ),
                )
                continue

            # SIZE-001: File effective line count.
            file_violations, file_warnings = _check_file_size(
                source=source,
                relative_file=relative_file,
            )
            violations.extend(file_violations)
            warnings.extend(file_warnings)

            # SIZE-002: Function/method length.
            func_violations, func_warnings = _check_function_lengths(
                tree=tree,
                relative_file=relative_file,
            )
            violations.extend(func_violations)
            warnings.extend(func_warnings)

            # SIZE-003: Class method count.
            warnings.extend(
                _check_class_method_count(tree=tree, relative_file=relative_file),
            )

            # SIZE-004: Cyclomatic complexity.
            complexity_violations, complexity_warnings = _check_function_metric(
                tree=tree,
                relative_file=relative_file,
                spec=_COMPLEXITY_SPEC,
            )
            violations.extend(complexity_violations)
            warnings.extend(complexity_warnings)

            # SIZE-005: Parameter count.
            param_violations, param_warnings = _check_function_metric(
                tree=tree,
                relative_file=relative_file,
                spec=_PARAM_SPEC,
            )
            violations.extend(param_violations)
            warnings.extend(param_warnings)

        status = Status.FAIL if violations else (Status.WARN if warnings else Status.PASS)
        return CheckResult(
            check=self.name,
            status=status,
            violations=violations,
            warnings=warnings,
        )


# Self-register on import.
register(FileLimitsCheck())
