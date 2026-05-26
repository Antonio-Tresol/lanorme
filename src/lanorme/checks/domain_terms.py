"""TERM-NNN: Domain terminology linter.

Enforces a project's canonical vocabulary across Python identifiers, comments,
and docstrings. Each rule maps one or more forbidden terms to the canonical
replacement; matches are word-boundary anchored and case-insensitive.

Configure the vocabulary in ``[tool.lanorme.domain_terms]``::

    [[tool.lanorme.domain_terms.rules]]
    id = "TERM-001"
    canonical = "Account"
    forbidden = ["Acct", "Acnt"]

With no configured rules the check is inert (always PASS), so it never produces
false positives on a project that has not defined a vocabulary.

Boundary exemptions: files named ``test_*`` and files under ``migrations/`` are
skipped.

Run:
    lanorme check . --check=domain_terms
"""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass, field
from pathlib import Path

from lanorme import CheckResult, Status, Violation, register

# Each rule maps forbidden terms to a canonical replacement. Empty by default →
# the check is inert until a project supplies its own vocabulary.
_RULES: list[dict[str, str | list[str]]] = []

_RuleSpec = tuple[str, str, re.Pattern[str]]  # (rule_id, canonical, compiled pattern)


def _compile_rules(rules: list[dict[str, str | list[str]]]) -> list[_RuleSpec]:
    compiled: list[_RuleSpec] = []
    for rule in rules:
        forbidden = rule.get("forbidden", [])
        if not isinstance(forbidden, list) or not forbidden:
            continue
        alternatives = "|".join(re.escape(str(term)) for term in forbidden)
        pattern = re.compile(rf"\b({alternatives})\b", re.IGNORECASE)
        compiled.append((str(rule["id"]), str(rule["canonical"]), pattern))
    return compiled


_SKIP_DIRS = ("migrations",)


def _is_exempt_path(*, relative_path: str) -> bool:
    normalized = relative_path.replace("\\", "/")
    name = Path(normalized).name
    if name.startswith("test_"):
        return True
    return any(normalized.startswith(f"{d}/") or f"/{d}/" in normalized for d in _SKIP_DIRS)


def _extract_comment(*, line: str) -> str | None:
    idx = line.find("#")
    return line[idx:] if idx != -1 else None


def _names_from_node(node: ast.AST) -> list[tuple[str, int]]:
    """Extract (identifier, line) pairs declared or referenced by a single AST node."""
    if isinstance(node, ast.ClassDef):
        return [(node.name, node.lineno)]
    if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
        pairs = [(node.name, node.lineno)]
        pairs.extend(
            (arg.arg, getattr(arg, "lineno", node.lineno))
            for arg in node.args.args + node.args.kwonlyargs
        )
        return pairs
    if isinstance(node, ast.Name):
        return [(node.id, getattr(node, "lineno", 0))]
    if isinstance(node, ast.Attribute):
        return [(node.attr, getattr(node, "lineno", 0))]
    if isinstance(node, ast.Assign):
        return [(t.id, node.lineno) for t in node.targets if isinstance(t, ast.Name)]
    if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
        return [(node.target.id, node.lineno)]
    return []


def _scan_identifiers(
    *,
    tree: ast.Module,
    relative_file: str,
    compiled: list[_RuleSpec],
) -> list[Violation]:
    """Walk the AST and check identifier names against the compiled rules."""
    violations: list[Violation] = []

    for node in ast.walk(tree):
        for name, lineno in _names_from_node(node):
            for rule_id, canonical, pattern in compiled:
                for match in pattern.finditer(name):
                    matched_term = match.group(1)
                    violations.append(
                        Violation(
                            file=relative_file,
                            line=lineno,
                            rule=f"{rule_id}: Use '{canonical}' instead of '{matched_term}'",
                            message=f"Forbidden term '{matched_term}' in identifier '{name}'",
                            fix=f"Rename — use '{canonical}' instead of '{matched_term}'",
                        ),
                    )

    return violations


def _scan_comments_and_docstrings(
    *,
    source_lines: list[str],
    tree: ast.Module,
    relative_file: str,
    compiled: list[_RuleSpec],
) -> list[Violation]:
    """Scan inline comments and docstrings for forbidden terms."""
    violations: list[Violation] = []

    def _scan_text(*, text: str, line_number: int) -> None:
        for rule_id, canonical, pattern in compiled:
            for match in pattern.finditer(text):
                matched_term = match.group(1)
                violations.append(
                    Violation(
                        file=relative_file,
                        line=line_number,
                        rule=f"{rule_id}: Use '{canonical}' instead of '{matched_term}'",
                        message=f"Forbidden term '{matched_term}' in comment/docstring",
                        fix=f"Replace '{matched_term}' with '{canonical}'",
                    ),
                )

    for lineno_0, line in enumerate(source_lines):
        stripped = line.lstrip()
        if stripped.startswith("import ") or stripped.startswith("from "):
            continue
        comment = _extract_comment(line=line)
        if comment:
            _scan_text(text=comment, line_number=lineno_0 + 1)

    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Module | ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef)
            and node.body
            and isinstance(node.body[0], ast.Expr)
            and isinstance(node.body[0].value, ast.Constant)
            and isinstance(node.body[0].value.value, str)
        ):
            const_node = node.body[0].value
            for i, doc_line in enumerate(str(const_node.value).splitlines()):
                _scan_text(text=doc_line, line_number=const_node.lineno + i)

    return violations


@dataclass
class DomainTermsCheck:
    """Enforces a project's canonical domain terminology."""

    name: str = "domain_terms"
    description: str = "Domain terminology linter (canonical vocabulary enforcement)"
    term_rules: list[dict[str, str | list[str]]] = field(default_factory=lambda: list(_RULES))
    rules: list[str] = field(
        default_factory=lambda: [
            "TERM-NNN: Use the canonical term instead of a configured forbidden synonym",
        ]
    )

    def configure(self, *, settings: dict[str, list[dict[str, str | list[str]]]]) -> None:
        """Apply ``[tool.lanorme.domain_terms]`` configuration."""
        self.term_rules = list(settings.get("rules", []))

    def run(self, *, src_root: str) -> CheckResult:
        violations: list[Violation] = []
        warnings: list[Violation] = []
        compiled = _compile_rules(self.term_rules)
        if not compiled:
            return CheckResult(check=self.name, status=Status.PASS, violations=[])

        src_path = Path(src_root)
        for py_file in sorted(src_path.rglob("*.py")):
            relative_file = str(py_file.relative_to(src_path))
            if _is_exempt_path(relative_path=relative_file):
                continue

            try:
                source = py_file.read_text(encoding="utf-8")
                tree = ast.parse(source, filename=str(py_file))
            except (OSError, UnicodeDecodeError, SyntaxError):
                warnings.append(
                    Violation(
                        file=relative_file,
                        line=0,
                        rule="TERM-000: parse error",
                        message=f"Could not parse {py_file.name} — skipping",
                        fix="Fix the syntax error first",
                    ),
                )
                continue

            violations.extend(
                _scan_identifiers(tree=tree, relative_file=relative_file, compiled=compiled),
            )
            violations.extend(
                _scan_comments_and_docstrings(
                    source_lines=source.splitlines(),
                    tree=tree,
                    relative_file=relative_file,
                    compiled=compiled,
                ),
            )

        status = Status.FAIL if violations else (Status.WARN if warnings else Status.PASS)
        return CheckResult(
            check=self.name,
            status=status,
            violations=violations,
            warnings=warnings,
        )


register(DomainTermsCheck())
