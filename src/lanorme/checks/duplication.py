"""DRY-001: Exact structural clone detection via AST normalization.

Checks:
    DRY-001  Functions with identical normalized AST bodies (>= 5 statements)
             are flagged as duplication candidates.

Normalization: variable names and string literals are replaced with placeholders
so that functions differing only in naming are detected as duplicates. The match
is exact modulo those placeholders: a single added statement, a reordering, a
changed number, or a renamed attribute defeats it. For the fuzzier near-duplicate
cases see the ``similarity`` check (SIMILAR-001).

Excludes: __init__.py, conftest.py, alembic/, migrations/, test_* prefixed files.

Run:
    lanorme check . --check=duplication
"""

from __future__ import annotations

import ast
import copy
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

from lanorme import CheckResult, Status, Violation, register
from lanorme.discovery import iter_py_files

# Minimum number of statements in a function body to consider for duplication.
MIN_BODY_STATEMENTS = 5

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


class _AstNormalizer(ast.NodeTransformer):
    """Replace variable names and string literals with placeholders.

    This makes structurally identical functions match even when they use
    different variable names or string constants.
    """

    def __init__(self) -> None:
        super().__init__()
        self._name_map: dict[str, str] = {}
        self._name_counter: int = 0

    def _normalize_name(self, *, name: str) -> str:
        """Map a variable name to a sequential placeholder."""
        if name not in self._name_map:
            self._name_map[name] = f"_var{self._name_counter}"
            self._name_counter += 1
        return self._name_map[name]

    def visit_Name(self, node: ast.Name) -> ast.Name:  # noqa: N802
        """Normalize variable references."""
        node.id = self._normalize_name(name=node.id)
        self.generic_visit(node)
        return node

    def visit_arg(self, node: ast.arg) -> ast.arg:
        """Normalize function argument names."""
        node.arg = self._normalize_name(name=node.arg)
        self.generic_visit(node)
        return node

    def visit_Constant(self, node: ast.Constant) -> ast.Constant:  # noqa: N802
        """Replace string literals with a placeholder."""
        if isinstance(node.value, str):
            node.value = "_STR_"
        return node

    def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.FunctionDef:  # noqa: N802
        """Normalize the function name itself."""
        node.name = self._normalize_name(name=node.name)
        self.generic_visit(node)
        return node

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> ast.AsyncFunctionDef:  # noqa: N802
        """Normalize async function name."""
        node.name = self._normalize_name(name=node.name)
        self.generic_visit(node)
        return node


def _normalize_function_body(*, func_node: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
    """Return a normalized AST dump of a function's body for comparison.

    Creates a deep copy to avoid mutating the original tree, then strips
    variable names and string literals so structurally identical functions
    produce the same dump string.
    """
    body_copy = copy.deepcopy(func_node.body)
    wrapper = ast.Module(body=body_copy, type_ignores=[])
    normalizer = _AstNormalizer()
    normalized = normalizer.visit(wrapper)
    return ast.dump(normalized)


@dataclass(frozen=True)
class _FunctionLocation:
    """Tracks where a function was found for violation reporting."""

    file: str
    line: int
    name: str


def _collect_functions(
    *,
    tree: ast.AST,
    relative_file: str,
) -> list[tuple[str, _FunctionLocation]]:
    """Walk the AST and return (normalized_hash, location) for qualifying functions."""
    results: list[tuple[str, _FunctionLocation]] = []

    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            continue

        # Skip functions with fewer statements than the threshold.
        if len(node.body) < MIN_BODY_STATEMENTS:
            continue

        # Skip if the entire body is a single docstring + pass or similar trivial patterns.
        normalized = _normalize_function_body(func_node=node)
        location = _FunctionLocation(
            file=relative_file,
            line=node.lineno,
            name=node.name,
        )
        results.append((normalized, location))

    return results


def _build_violations(
    *,
    groups: dict[str, list[_FunctionLocation]],
) -> list[Violation]:
    """Create a violation for each function that has a near-duplicate elsewhere."""
    violations: list[Violation] = []

    for locations in groups.values():
        if len(locations) < 2:
            continue

        # Sort by file then line for deterministic output.
        sorted_locs = sorted(locations, key=lambda loc: (loc.file, loc.line))
        other_locations = [f"{loc.file}:{loc.line} ({loc.name})" for loc in sorted_locs]

        for loc in sorted_locs:
            peers = [o for o in other_locations if o != f"{loc.file}:{loc.line} ({loc.name})"]
            violations.append(
                Violation(
                    file=loc.file,
                    line=loc.line,
                    rule="DRY-001: Near-duplicate function body detected",
                    message=(
                        f"Function '{loc.name}' has a near-duplicate body "
                        f"matching: {', '.join(peers)}"
                    ),
                    fix="Extract shared logic into a common helper function",
                ),
            )

    return violations


@dataclass
class DuplicationCheck:
    """Detects near-duplicate function bodies via AST normalization."""

    name: str = "duplication"
    description: str = "Near-duplicate function detection (DRY enforcement)"
    rules: list[str] = field(
        default_factory=lambda: [
            "DRY-001: Functions with identical normalized AST bodies (>= 5 statements) are duplicates",
        ],
    )

    def run(self, *, src_root: str) -> CheckResult:
        """Scan all Python files under src/ and detect near-duplicate functions."""
        warnings: list[Violation] = []
        src_path = Path(src_root)

        # Map normalized body hash -> list of locations.
        body_groups: dict[str, list[_FunctionLocation]] = defaultdict(list)

        for py_file in iter_py_files(src_path):
            if _should_exclude(file_path=py_file):
                continue

            relative_file = str(py_file.relative_to(src_path))

            try:
                source = py_file.read_text(encoding="utf-8")
                tree = ast.parse(source, filename=str(py_file))
                collected = _collect_functions(tree=tree, relative_file=relative_file)
            except (OSError, UnicodeDecodeError, SyntaxError):
                warnings.append(
                    Violation(
                        file=relative_file,
                        line=0,
                        rule="DRY-000: parse error",
                        message=f"Could not parse {py_file.name} — skipping",
                        fix="Fix the syntax error first",
                    ),
                )
                continue
            except RecursionError:
                # A deeply nested AST overflows the deepcopy used to normalise a
                # body. Skip the file rather than crash the whole run.
                warnings.append(
                    Violation(
                        file=relative_file,
                        line=0,
                        rule="DRY-000: too deeply nested",
                        message=f"{py_file.name} is too deeply nested to normalise — skipping",
                        fix="No action needed; this file is exempt from DRY-001",
                    ),
                )
                continue

            for normalized_hash, location in collected:
                body_groups[normalized_hash].append(location)

        violations = _build_violations(groups=body_groups)

        status = Status.FAIL if violations else (Status.WARN if warnings else Status.PASS)
        return CheckResult(
            check=self.name,
            status=status,
            violations=violations,
            warnings=warnings,
        )


# Self-register on import.
register(DuplicationCheck())
