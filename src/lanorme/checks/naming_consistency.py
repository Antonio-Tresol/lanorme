"""NAMING-001 through NAMING-004: Naming convention enforcement.

Checks:
    NAMING-001  Repository methods must use get_/create_/update_/delete_/list_ prefixes
    NAMING-002  Service methods must use get_/create_/update_/delete_/list_ prefixes
    NAMING-003  Endpoint handlers should match HTTP verb (warning only)
    NAMING-004  Boolean functions should use is_/has_/can_/should_ prefixes (warning only)

Run:
    lanorme check . --check=naming_consistency
"""

from __future__ import annotations

import ast
from dataclasses import dataclass, field
from pathlib import Path

from lanorme import CheckResult, Status, Violation, register

# Allowed public method prefixes for repositories and services.
ALLOWED_PREFIXES = ("get_", "create_", "update_", "delete_", "list_")

# Forbidden prefixes with their suggested replacement.
FORBIDDEN_PREFIX_MAP: dict[str, str] = {
    "fetch_": "get_",
    "retrieve_": "get_",
    "find_": "get_",
    "remove_": "delete_",
    "add_": "create_",
}

# Expected handler prefix per HTTP method (NAMING-003).
HTTP_VERB_PREFIXES: dict[str, tuple[str, ...]] = {
    "get": ("get_", "list_"),
    "post": ("create_",),
    "put": ("update_",),
    "delete": ("delete_",),
}

# Endpoint names that are exempt from verb-matching: auth-issuance flows and
# health/readiness probes, which do not follow CRUD verb conventions.
VERB_EXEMPT_ENDPOINTS = frozenset(
    {
        # Auth-issuance handlers.
        "login",
        "logout",
        "refresh",
        "token",
        # Health probes.
        "health",
        "health_check",
        "ready",
        "readiness_check",
    }
)

# Boolean-appropriate prefixes (NAMING-004).
BOOL_PREFIXES = ("is_", "has_", "can_", "should_")

# Directories (relative to the source root) to scan for each rule.
REPO_DIRS = ("infrastructure/repositories", "infrastructure/persistence")
SERVICE_DIRS = ("application/services",)
ENDPOINT_DIRS = ("api/v1/endpoints",)


def _extract_public_class_methods(
    *,
    tree: ast.Module,
) -> list[tuple[str, str, int]]:
    """Extract public method names from all classes in a module.

    Returns:
        List of (class_name, method_name, line_number) tuples for public methods.
    """
    results: list[tuple[str, str, int]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        for item in node.body:
            if not isinstance(item, ast.FunctionDef | ast.AsyncFunctionDef):
                continue
            if item.name.startswith("_"):
                continue
            results.append((node.name, item.name, item.lineno))
    return results


def _check_forbidden_prefixes(
    *,
    method_name: str,
) -> tuple[str, str] | None:
    """Check if a method uses a forbidden prefix.

    Returns:
        (forbidden_prefix, suggested_prefix) if found, else None.
    """
    for forbidden, suggested in FORBIDDEN_PREFIX_MAP.items():
        if method_name.startswith(forbidden):
            return (forbidden, suggested)
    return None


def _check_repo_and_service_naming(
    *,
    tree: ast.Module,
    relative_file: str,
    rule: str,
    layer_label: str,
) -> list[Violation]:
    """NAMING-001 / NAMING-002: Check method prefixes on classes."""
    violations: list[Violation] = []
    methods = _extract_public_class_methods(tree=tree)

    for class_name, method_name, line in methods:
        match = _check_forbidden_prefixes(method_name=method_name)
        if match is None:
            continue
        forbidden, suggested = match
        violations.append(
            Violation(
                file=relative_file,
                line=line,
                rule=rule,
                message=(
                    f"{layer_label} method '{class_name}.{method_name}' "
                    f"uses forbidden prefix '{forbidden}'"
                ),
                fix=f"Rename to '{suggested}{method_name[len(forbidden) :]}'",
            ),
        )

    return violations


def _extract_http_method_from_decorator(
    *,
    decorator: ast.expr,
) -> str | None:
    """Extract the HTTP method from a @router.<method>(...) decorator."""
    if not isinstance(decorator, ast.Call):
        return None
    if not isinstance(decorator.func, ast.Attribute):
        return None
    method = decorator.func.attr
    if method in HTTP_VERB_PREFIXES:
        return method
    return None


def _check_endpoint_verb_naming(
    *,
    tree: ast.Module,
    relative_file: str,
) -> list[Violation]:
    """NAMING-003: Endpoint handler names should match HTTP verb."""
    warnings: list[Violation] = []

    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            continue

        if node.name in VERB_EXEMPT_ENDPOINTS:
            continue

        for decorator in node.decorator_list:
            http_method = _extract_http_method_from_decorator(decorator=decorator)
            if http_method is None:
                continue

            expected_prefixes = HTTP_VERB_PREFIXES[http_method]
            if not any(node.name.startswith(prefix) for prefix in expected_prefixes):
                expected_str = " or ".join(f"'{p}'" for p in expected_prefixes)
                warnings.append(
                    Violation(
                        file=relative_file,
                        line=node.lineno,
                        rule=(
                            f"NAMING-003: @router.{http_method} handler "
                            f"should use {expected_str} prefix"
                        ),
                        message=(
                            f"Handler '{node.name}' is a {http_method.upper()} endpoint "
                            f"but does not start with {expected_str}"
                        ),
                        fix=(
                            f"Rename to '{expected_prefixes[0]}{node.name}' "
                            f"or add '{node.name}' to VERB_EXEMPT_ENDPOINTS if intentional"
                        ),
                    ),
                )
            break  # Only check the first matching decorator per function.

    return warnings


def _has_bool_return_annotation(*, node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    """Check if a function has a -> bool return type annotation."""
    annotation = node.returns
    if annotation is None:
        return False
    if isinstance(annotation, ast.Name) and annotation.id == "bool":
        return True
    return isinstance(annotation, ast.Constant) and annotation.value == "bool"


def _check_bool_naming(
    *,
    tree: ast.Module,
    relative_file: str,
) -> list[Violation]:
    """NAMING-004: Boolean functions should use is_/has_/can_/should_ prefix."""
    warnings: list[Violation] = []

    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            continue

        if node.name.startswith("_"):
            continue

        if not _has_bool_return_annotation(node=node):
            continue

        if any(node.name.startswith(prefix) for prefix in BOOL_PREFIXES):
            continue

        warnings.append(
            Violation(
                file=relative_file,
                line=node.lineno,
                rule="NAMING-004: Boolean functions should use is_/has_/can_/should_ prefix",
                message=f"Function '{node.name}' returns bool but lacks a boolean prefix",
                fix=f"Rename to 'is_{node.name}' or another boolean prefix (has_, can_, should_)",
            ),
        )

    return warnings


def _file_is_under(*, relative_path: str, directories: tuple[str, ...]) -> bool:
    """Check if a relative path falls under one of the given directories."""
    normalized = relative_path.replace("\\", "/")
    return any(normalized.startswith(f"{d}/") for d in directories)


@dataclass
class NamingConsistencyCheck:
    """Validates naming conventions for repositories, services, endpoints, and booleans."""

    name: str = "naming_consistency"
    description: str = "Naming convention enforcement (methods, endpoints, booleans)"
    # NAMING-001 / NAMING-002 (CRUD prefixes) ship default-off: the audit
    # surfaced that they actively suppress the ubiquitous-language verbs
    # the TERM check exists to protect (approve_loan, transfer_funds, etc.).
    # Opt in via [tool.lanorme.naming_consistency] repo_crud = true / service_crud = true.
    repo_crud: bool = False
    service_crud: bool = False
    rules: list[str] = field(
        default_factory=lambda: [
            "NAMING-001: Repository methods must use get_/create_/update_/delete_/list_ prefixes (opt-in)",
            "NAMING-002: Service methods must use get_/create_/update_/delete_/list_ prefixes (opt-in)",
            "NAMING-003: Endpoint handlers should match HTTP verb (warning)",
            "NAMING-004: Boolean functions should use is_/has_/can_/should_ prefix (warning)",
        ],
    )

    def configure(self, *, settings: dict[str, bool]) -> None:
        """Apply ``[tool.lanorme.naming_consistency]`` configuration."""
        if "repo_crud" in settings:
            self.repo_crud = bool(settings["repo_crud"])
        if "service_crud" in settings:
            self.service_crud = bool(settings["service_crud"])

    def run(self, *, src_root: str) -> CheckResult:
        """Scan source files and validate naming conventions."""
        violations: list[Violation] = []
        warnings: list[Violation] = []
        src_path = Path(src_root)

        for py_file in sorted(src_path.rglob("*.py")):
            relative_file = str(py_file.relative_to(src_path))

            try:
                source = py_file.read_text(encoding="utf-8")
                tree = ast.parse(source, filename=str(py_file))
            except (OSError, UnicodeDecodeError, SyntaxError):
                continue

            # NAMING-001: Repository method naming (opt-in; conflicts with DDD ubiquitous-language).
            if self.repo_crud and _file_is_under(relative_path=relative_file, directories=REPO_DIRS):
                violations.extend(
                    _check_repo_and_service_naming(
                        tree=tree,
                        relative_file=relative_file,
                        rule="NAMING-001: Repository methods must use get_/create_/update_/delete_/list_ prefixes",
                        layer_label="Repository",
                    ),
                )

            # NAMING-002: Service method naming (opt-in; conflicts with DDD ubiquitous-language).
            if self.service_crud and _file_is_under(relative_path=relative_file, directories=SERVICE_DIRS):
                violations.extend(
                    _check_repo_and_service_naming(
                        tree=tree,
                        relative_file=relative_file,
                        rule="NAMING-002: Service methods must use get_/create_/update_/delete_/list_ prefixes",
                        layer_label="Service",
                    ),
                )

            # NAMING-003: Endpoint handler verb matching (warning only).
            if _file_is_under(relative_path=relative_file, directories=ENDPOINT_DIRS):
                warnings.extend(
                    _check_endpoint_verb_naming(
                        tree=tree,
                        relative_file=relative_file,
                    ),
                )

            # NAMING-004: Boolean function prefixes (warning only, all files).
            warnings.extend(
                _check_bool_naming(
                    tree=tree,
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
register(NamingConsistencyCheck())
