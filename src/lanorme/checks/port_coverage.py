"""PORT-001 through PORT-003: Port coverage enforcement for hexagonal architecture.

Verifies that infrastructure services implement port Protocols, that every
Protocol has at least one implementation, and that the API layer does not
directly instantiate infrastructure service classes.

Rules:
    PORT-001  Every non-utility file in infrastructure/services/ must
              import from application/ports/ (structural subtyping link)
    PORT-002  Every Protocol in application/ports/ (excluding repositories,
              unit_of_work, and otel) must be referenced by at
              least one infrastructure service file
    PORT-003  No direct import of infrastructure service classes in the
              api/ layer outside the composition root (api/*/dependencies/)

Run:
    lanorme check . --check=port_coverage
"""

from __future__ import annotations

import ast
from dataclasses import dataclass, field
from pathlib import Path

from lanorme import CheckResult, Status, Violation, register

# Files under each infrastructure adapter directory that are pure utilities
# or re-exports (not concrete port implementations).
INFRA_SERVICE_SKIP_FILES = {
    "__init__.py",
}

# Port files whose Protocols are implemented in infrastructure/repositories/,
# infrastructure/db/, or infrastructure/observability/ rather than infrastructure/services/.
PORT_FILES_WITHOUT_SERVICE_IMPL = {
    "repositories.py",
    "unit_of_work.py",
    "otel.py",
    "metrics.py",
}

# The composition root patterns, api/ files matching these are exempt from
# PORT-003 because DI wiring legitimately references infrastructure.
COMPOSITION_ROOT_PATTERNS = ("dependencies/", "v1/main.py")


# ---- AST helpers -----------------------------------------------------------


def _extract_protocol_names(*, tree: ast.AST) -> list[tuple[str, int]]:
    """Find all ``class Foo(Protocol): ...`` definitions in an AST.

    Returns:
        List of (class_name, line_number) tuples.
    """
    protocols: list[tuple[str, int]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        for base in node.bases:
            base_name: str | None = None
            if isinstance(base, ast.Name):
                base_name = base.id
            elif isinstance(base, ast.Attribute):
                base_name = base.attr
            if base_name == "Protocol":
                protocols.append((node.name, node.lineno))
                break
    return protocols


def _extract_import_modules(*, tree: ast.AST) -> list[tuple[str, int]]:
    """Extract all import source modules as (dotted_module, line) pairs.

    For ``from x.y import z`` this yields ``("x.y", line)``.
    For ``import x.y`` this yields ``("x.y", line)``.
    """
    modules: list[tuple[str, int]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                modules.append((alias.name, node.lineno))
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.append((node.module, node.lineno))
    return modules


def _extract_imported_names(*, tree: ast.AST) -> set[str]:
    """Collect all names brought into scope via import statements."""
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                names.add(alias.asname if alias.asname else alias.name.split(".")[-1])
        elif isinstance(node, ast.ImportFrom):
            for alias in node.names or []:
                names.add(alias.asname if alias.asname else alias.name)
    return names


def _extract_call_names(*, tree: ast.AST) -> list[tuple[str, int]]:
    """Find ``SomeClass(...)`` call expressions and return (name, line)."""
    calls: list[tuple[str, int]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                calls.append((node.func.id, node.lineno))
            elif isinstance(node.func, ast.Attribute):
                calls.append((node.func.attr, node.lineno))
    return calls


def _extract_top_level_class_names(*, tree: ast.AST) -> list[str]:
    """Get top-level class names from an AST (non-nested)."""
    return [node.name for node in ast.iter_child_nodes(tree) if isinstance(node, ast.ClassDef)]


def _imports_from_ports(*, import_modules: list[tuple[str, int]]) -> bool:
    """Return True if any import comes from ``application.ports`` or ``src.application.ports``."""
    return any("application.ports" in module for module, _line in import_modules)


def _port_module_stem(*, module: str) -> str | None:
    """Extract the port module filename stem from a dotted import path.

    ``src.application.ports.registry`` → ``registry``
    ``application.ports.services`` → ``services``
    Returns None if the module is not a ports import.
    """
    parts = module.split(".")
    # Match both src.application.ports.X and application.ports.X
    for i, part in enumerate(parts):
        if part == "ports" and i >= 1 and parts[i - 1] == "application":
            if i + 1 < len(parts):
                return parts[i + 1]
            return None
    return None


def _parse_file(*, py_file: Path) -> ast.AST | None:
    """Parse a Python file, returning None on syntax errors."""
    try:
        source = py_file.read_text(encoding="utf-8")
        return ast.parse(source, filename=str(py_file))
    except (OSError, UnicodeDecodeError, SyntaxError):
        return None


# ---- Scanning --------------------------------------------------------------


def _collect_port_protocols(
    *,
    src_path: Path,
) -> dict[str, tuple[str, int, str]]:
    """Scan ``application/ports/`` and return Protocol metadata.

    Returns:
        {ProtocolName: (relative_file, line, port_module_stem)}
    """
    protocols: dict[str, tuple[str, int, str]] = {}
    ports_dir = src_path / "application" / "ports"
    if not ports_dir.is_dir():
        return protocols

    for py_file in sorted(ports_dir.glob("*.py")):
        if py_file.name == "__init__.py":
            continue
        if py_file.name in PORT_FILES_WITHOUT_SERVICE_IMPL:
            continue

        tree = _parse_file(py_file=py_file)
        if tree is None:
            continue

        relative = str(py_file.relative_to(src_path))
        stem = py_file.stem

        for name, line in _extract_protocol_names(tree=tree):
            protocols[name] = (relative, line, stem)

    return protocols


def _scan_infra_service_files(
    *,
    src_path: Path,
) -> list[tuple[str, ast.AST, list[tuple[str, int]]]]:
    """Scan ``infrastructure/services/`` and return parsed file data.

    Returns:
        List of (relative_file, ast_tree, import_modules).
    """
    results: list[tuple[str, ast.AST, list[tuple[str, int]]]] = []
    services_dir = src_path / "infrastructure" / "services"
    if not services_dir.is_dir():
        return results

    for py_file in sorted(services_dir.glob("*.py")):
        if py_file.name in INFRA_SERVICE_SKIP_FILES:
            continue

        tree = _parse_file(py_file=py_file)
        if tree is None:
            continue

        relative = str(py_file.relative_to(src_path))
        imports = _extract_import_modules(tree=tree)
        results.append((relative, tree, imports))

    return results


# ---- Rule implementations -------------------------------------------------


def _check_port001(
    *,
    infra_files: list[tuple[str, ast.AST, list[tuple[str, int]]]],
) -> list[Violation]:
    """PORT-001: Every infra service file must import from application/ports/."""
    violations: list[Violation] = []

    for relative_file, _tree, import_modules in infra_files:
        if _imports_from_ports(import_modules=import_modules):
            continue

        violations.append(
            Violation(
                file=relative_file,
                line=1,
                rule="PORT-001: Infrastructure service must implement a port Protocol",
                message=(f"File '{relative_file}' has no imports from application/ports/"),
                fix=(
                    "Import and implement the corresponding Protocol from application/ports/, "
                    "or add the file to INFRA_SERVICE_SKIP_FILES if it is a pure utility"
                ),
            ),
        )

    return violations


def _check_port002(
    *,
    port_protocols: dict[str, tuple[str, int, str]],
    infra_files: list[tuple[str, ast.AST, list[tuple[str, int]]]],
) -> list[Violation]:
    """PORT-002: Every port Protocol must be backed by an infra service file."""
    violations: list[Violation] = []

    # Build a set of port module stems imported by any infrastructure service file.
    referenced_port_stems: set[str] = set()
    for _relative, _tree, import_modules in infra_files:
        for module, _line in import_modules:
            stem = _port_module_stem(module=module)
            if stem is not None:
                referenced_port_stems.add(stem)

    for proto_name, (relative_file, line, port_stem) in sorted(port_protocols.items()):
        if port_stem in referenced_port_stems:
            continue

        violations.append(
            Violation(
                file=relative_file,
                line=line,
                rule="PORT-002: Port Protocol has no infrastructure implementation",
                message=(
                    f"Protocol '{proto_name}' (in ports/{port_stem}.py) "
                    "is not imported by any infrastructure service"
                ),
                fix=(
                    "Create an implementation in infrastructure/services/ that imports "
                    "from this port module, or add the port file to PORT_FILES_WITHOUT_SERVICE_IMPL"
                ),
            ),
        )

    return violations


def _direct_import_violation(
    *,
    relative: str,
    import_modules: list[tuple[str, int]],
    imported_infra: set[str],
) -> Violation | None:
    """Report an api/ file importing infra service classes outside the composition root."""
    for module, line in import_modules:
        if "infrastructure.services" in module:
            return Violation(
                file=relative,
                line=line,
                rule="PORT-003: Direct import of infra service in api/ layer",
                message=(
                    f"Imports infrastructure service class(es) "
                    f"{sorted(imported_infra)} outside composition root"
                ),
                fix=(
                    "Depend on the port Protocol from application/ports/ instead, "
                    "or move the import to api/v1/dependencies/"
                ),
            )
    return None


def _check_port003(
    *,
    src_path: Path,
    infra_class_names: set[str],
) -> list[Violation]:
    """PORT-003: No direct import of infra service classes in api/ layer."""
    violations: list[Violation] = []

    api_dir = src_path / "api"
    if not api_dir.is_dir():
        return violations

    for py_file in sorted(api_dir.rglob("*.py")):
        relative = str(py_file.relative_to(src_path)).replace("\\", "/")

        # Skip composition root, DI wiring is allowed there.
        if any(pattern in relative for pattern in COMPOSITION_ROOT_PATTERNS):
            continue

        tree = _parse_file(py_file=py_file)
        if tree is None:
            continue

        # Check: does this file import from infrastructure.services?
        import_modules = _extract_import_modules(tree=tree)
        imports_infra = any(
            "infrastructure.services" in module or "infrastructure/services" in module
            for module, _line in import_modules
        )
        if not imports_infra:
            continue

        # Which infra class names does this file actually import?
        imported_names = _extract_imported_names(tree=tree)
        imported_infra = imported_names & infra_class_names

        if not imported_infra:
            continue

        # Report each direct instantiation of an infra class.
        found_instantiation = False
        for call_name, call_line in _extract_call_names(tree=tree):
            if call_name in imported_infra:
                violations.append(
                    Violation(
                        file=relative,
                        line=call_line,
                        rule="PORT-003: Direct instantiation of infra service in api/ layer",
                        message=f"'{call_name}(...)' instantiated directly — use dependency injection",
                        fix=(
                            "Move the construction to api/dependencies/ and inject "
                            "it through your dependency-injection layer"
                        ),
                    ),
                )
                found_instantiation = True

        # Even if not instantiated, importing infra service classes in api/
        # (outside composition root) is a smell, report the import itself.
        if not found_instantiation:
            import_violation = _direct_import_violation(
                relative=relative,
                import_modules=import_modules,
                imported_infra=imported_infra,
            )
            if import_violation is not None:
                violations.append(import_violation)

    return violations


# ---- Check class -----------------------------------------------------------


@dataclass
class PortCoverageCheck:
    """Validates port/adapter coverage in the hexagonal architecture."""

    name: str = "port_coverage"
    description: str = "Port coverage enforcement (Protocol / infrastructure alignment)"
    rules: list[str] = field(
        default_factory=lambda: [
            "PORT-001: Every infrastructure service file must import from application/ports/",
            "PORT-002: Every port Protocol must have at least one infrastructure implementation",
            "PORT-003: No direct import/instantiation of infrastructure services in api/ layer",
        ],
    )

    def run(self, *, src_root: str) -> CheckResult:
        """Scan ports and infrastructure services and validate coverage."""
        violations: list[Violation] = []
        warnings: list[Violation] = []
        src_path = Path(src_root)

        # Collect data from both sides of the hexagonal boundary.
        port_protocols = _collect_port_protocols(src_path=src_path)
        infra_files = _scan_infra_service_files(src_path=src_path)

        # PORT-001: Every infra service file imports from application/ports/.
        violations.extend(
            _check_port001(infra_files=infra_files),
        )

        # PORT-002: Every port Protocol has an infra implementation.
        violations.extend(
            _check_port002(
                port_protocols=port_protocols,
                infra_files=infra_files,
            ),
        )

        # PORT-003: No direct import/instantiation in api/ layer.
        infra_class_names: set[str] = set()
        for _relative, tree, _imports in infra_files:
            infra_class_names.update(_extract_top_level_class_names(tree=tree))

        violations.extend(
            _check_port003(
                src_path=src_path,
                infra_class_names=infra_class_names,
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
register(PortCoverageCheck())
