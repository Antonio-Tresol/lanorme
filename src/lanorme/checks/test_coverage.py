"""TEST-001 and TEST-002: Test quality enforcement checks.

TEST-001  Every production module under the source root (endpoints,
          services, adapters) must have a corresponding test module in
          tests/.
TEST-002  Test functions with >5 code lines must follow the AAA
          (Arrange-Act-Assert) pattern with at least 2 blank-line separators.

Both rules are advisory (WARNING), new modules need time to get tests,
and the AAA pattern is a style guide rather than a hard requirement.

Run:
    lanorme check . --check=test_coverage
"""

from __future__ import annotations

import ast
from dataclasses import dataclass, field
from pathlib import Path

from lanorme import CheckResult, Status, Violation, register

# Minimum number of non-blank code lines before AAA enforcement kicks in.
_AAA_MIN_LINES = 5

# Number of blank-line separators expected in a well-structured AAA test.
_AAA_MIN_SEPARATORS = 2


# ---------------------------------------------------------------------------
# TEST-001 helpers
# ---------------------------------------------------------------------------


"""Directories under src/ that contain testable production modules.

Each entry maps a directory (relative to src/) to the import path pattern
used when searching test files for corresponding imports. Modules in these
directories should each have at least one test.
"""
_TESTABLE_DIRS: list[tuple[str, str]] = [
    ("api/v1/endpoints", "endpoints"),
    ("application/services", "services"),
    ("application/commands", "commands"),
    ("application/queries", "queries"),
    ("infrastructure/repositories", "infrastructure.repositories"),
    ("infrastructure/signing", "infrastructure.signing"),
    ("infrastructure/secrets", "infrastructure.secrets"),
]

# Modules that are intentionally untested (pure Protocol definitions,
# config files, composition roots, etc.).
_EXEMPT_MODULES: set[str] = {
    "dependencies",  # DI wiring, tested via endpoint tests
    "main",  # App composition root
    "logging",  # Logging setup
    "session",  # DB session factory
}


def _find_production_modules(*, src_root: str) -> list[tuple[str, str, str]]:
    """Find all testable production modules across src/.

    Returns:
        List of (relative_path, module_name, import_hint) tuples.
        import_hint is the dotted path fragment used to search test imports.
    """
    modules: list[tuple[str, str, str]] = []
    src_path = Path(src_root)

    for dir_rel, import_prefix in _TESTABLE_DIRS:
        target_dir = src_path / dir_rel
        if not target_dir.is_dir():
            continue

        for py_file in sorted(target_dir.glob("*.py")):
            name = py_file.stem
            if name.startswith("_"):
                continue
            if name in _EXEMPT_MODULES:
                continue

            rel_path = str(py_file.relative_to(src_path.parent))
            modules.append((rel_path, name, import_prefix))

    return modules


def _find_test_files(*, backend_root: Path) -> list[Path]:
    """Return all test_*.py files under tests/integration/."""
    tests_dir = backend_root / "tests" / "integration"
    if not tests_dir.is_dir():
        return []
    return sorted(tests_dir.glob("test_*.py"))


def _module_has_test(
    *,
    module_name: str,
    import_hint: str,
    test_stems: set[str],
    test_file_contents: dict[str, str],
) -> bool:
    """Check if a production module has a corresponding test file.

    Matches by:
    1. Exact name: test_{module_name}.py
    2. Shortened name: test_{name_without_last_word}.py (e.g. evals_runner -> evals)
    3. Any test file that imports from the module (using import_hint).
    """
    # Exact match.
    if f"test_{module_name}" in test_stems:
        return True

    # Shortened name, strip the last underscore-separated segment.
    parts = module_name.split("_")
    if len(parts) > 1:
        shortened = "_".join(parts[:-1])
        if f"test_{shortened}" in test_stems:
            return True

    # Import-based match, look for any test file importing the module.
    import_patterns = (
        f"{import_hint}.{module_name}",
        f"{import_hint} import {module_name}",
    )
    for contents in test_file_contents.values():
        if any(pattern in contents for pattern in import_patterns):
            return True

    return False


def _check_module_coverage(
    *,
    src_root: str,
    backend_root: Path,
) -> list[Violation]:
    """TEST-001: verify every production module has a corresponding test."""
    modules = _find_production_modules(src_root=src_root)
    test_files = _find_test_files(backend_root=backend_root)
    test_stems = {f.stem for f in test_files}

    # Pre-read test file contents for import-based matching.
    test_file_contents: dict[str, str] = {}
    for tf in test_files:
        try:
            test_file_contents[tf.stem] = tf.read_text(encoding="utf-8")
        except OSError:
            continue

    warnings: list[Violation] = []
    for rel_path, name, import_hint in modules:
        if not _module_has_test(
            module_name=name,
            import_hint=import_hint,
            test_stems=test_stems,
            test_file_contents=test_file_contents,
        ):
            warnings.append(
                Violation(
                    file=rel_path,
                    line=1,
                    rule="TEST-001: Every production module must have a corresponding test",
                    message=f"No test file found for module '{name}'",
                    fix=(
                        f"Create tests/integration/test_{name}.py with at least one "
                        f"integration test for {name}"
                    ),
                ),
            )

    return warnings


# ---------------------------------------------------------------------------
# TEST-002 helpers
# ---------------------------------------------------------------------------


def _count_code_lines_and_separators(
    *,
    lines: list[str],
) -> tuple[int, int]:
    """Count non-blank code lines and blank-line separators in a block.

    Returns:
        Tuple of (code_line_count, blank_separator_count).
    """
    code_lines = 0
    separators = 0
    prev_was_blank = False

    for line in lines:
        stripped = line.strip()
        is_blank = stripped == ""

        if is_blank:
            # Only count a separator once per blank region, and only if
            # we already have at least one code line above.
            if not prev_was_blank and code_lines > 0:
                separators += 1
            prev_was_blank = True
        else:
            # Skip comments, they don't count as code but don't break blocks.
            if stripped.startswith("#"):
                continue
            code_lines += 1
            prev_was_blank = False

    return code_lines, separators


def _check_aaa_pattern(*, backend_root: Path) -> list[Violation]:
    """TEST-002: verify test functions follow the AAA pattern."""
    warnings: list[Violation] = []
    tests_dir = backend_root / "tests"
    if not tests_dir.is_dir():
        return warnings

    for py_file in sorted(tests_dir.rglob("*.py")):
        # Skip conftest, __init__, non-test files.
        if not py_file.stem.startswith("test_"):
            continue

        try:
            source = py_file.read_text(encoding="utf-8")
            source_lines = source.splitlines()
            tree = ast.parse(source, filename=str(py_file))
        except (OSError, UnicodeDecodeError, SyntaxError):
            continue

        relative_path = str(py_file.relative_to(backend_root))

        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            if not node.name.startswith("test_"):
                continue

            # Determine function body line range.
            # node.lineno is the 'def' line; first body statement starts later.
            if not node.body:
                continue

            body_start = node.body[0].lineno
            body_end = node.end_lineno
            if body_end is None:
                continue

            # Extract body lines (0-indexed slicing, lineno is 1-indexed).
            body_lines = source_lines[body_start - 1 : body_end]

            code_lines, separators = _count_code_lines_and_separators(
                lines=body_lines,
            )

            # Exempt short tests, they're simple enough to be one block.
            if code_lines <= _AAA_MIN_LINES:
                continue

            if separators < _AAA_MIN_SEPARATORS:
                warnings.append(
                    Violation(
                        file=relative_path,
                        line=node.lineno,
                        rule="TEST-002: Test functions must follow the AAA pattern",
                        message=(
                            f"Test '{node.name}' has {code_lines} code lines but only "
                            f"{separators} blank-line separator(s) (expected >= {_AAA_MIN_SEPARATORS})"
                        ),
                        fix=(
                            "Add blank lines to separate Arrange, Act, and Assert blocks. "
                            "Example: setup code, then blank line, then the action, then "
                            "blank line, then assertions."
                        ),
                    ),
                )

    return warnings


# ---------------------------------------------------------------------------
# Check class and registration
# ---------------------------------------------------------------------------


@dataclass
class TestCoverageCheck:
    """Validates test quality: endpoint coverage and AAA pattern adherence."""

    name: str = "test_coverage"
    description: str = "Test quality checks: endpoint coverage and AAA pattern"
    rules: list[str] = field(
        default_factory=lambda: [
            "TEST-001: Every production module must have a corresponding test",
            "TEST-002: Test functions must follow the AAA pattern",
        ],
    )

    def run(self, *, src_root: str) -> CheckResult:
        """Run both test quality checks and return combined results."""
        # Derive backend_root from src_root (src_root is .../src).
        backend_root = Path(src_root).parent

        coverage_warnings = _check_module_coverage(
            src_root=src_root,
            backend_root=backend_root,
        )
        aaa_warnings = _check_aaa_pattern(backend_root=backend_root)

        all_warnings = coverage_warnings + aaa_warnings

        status = Status.WARN if all_warnings else Status.PASS
        return CheckResult(
            check=self.name,
            status=status,
            warnings=all_warnings,
        )


# Self-register on import.
register(TestCoverageCheck())
