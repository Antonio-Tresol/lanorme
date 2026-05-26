"""LAYER-001 through LAYER-005: Hexagonal layer dependency validation.

Uses Python's ast module to parse imports statically, no runtime execution.
Each file's layer is determined by its path under the source root. A file's
top-level package prefix (``mypkg.domain.models``) is stripped before the layer
is classified, so the check is package-name agnostic.

Dependency rules (inward only):
    domain/           → nothing else in the source tree (pure Python + stdlib)
    application/      → domain/ only
    infrastructure/   → domain/ + application/ only
    api/              → domain/ + application/ only
    api/dependencies/ → EXCEPTION: also allowed infrastructure/ (composition root)

Projects that do not use these layer directories produce no findings, the
check is naturally inert outside a four-layer hexagonal layout.

Run:
    lanorme check . --check=layer_deps
"""

from __future__ import annotations

import ast
from dataclasses import dataclass, field
from pathlib import Path

from lanorme import CheckResult, Status, Violation, register

# The architectural layers in a hexagonal backend.
LAYERS = ("domain", "application", "infrastructure", "api")

# What each layer is ALLOWED to import from within the source tree.
# Empty set = no inter-layer imports allowed.
ALLOWED_IMPORTS: dict[str, set[str]] = {
    "domain": set(),
    "application": {"domain"},
    "infrastructure": {"domain", "application"},
    "api": {"domain", "application"},
}

# Composition root exception: files under api/dependencies/ (DI wiring) and the
# application factory may import from infrastructure/ to bind ports to adapters.
COMPOSITION_ROOT_PATTERNS = (
    "api/dependencies/",
    "api/v1/dependencies/",
    "api/v1/main.py",
)

RULE_MAP = {
    "domain": "LAYER-001: domain/ must not import from any other layer (pure Python only)",
    "application": "LAYER-002: application/ can only import from domain/",
    "infrastructure": "LAYER-003: infrastructure/ can only import from domain/ and application/",
    "api": "LAYER-004: api/ can only import from domain/ and application/",
    "api_composition": "LAYER-005: only api/dependencies/ may import from infrastructure/ (composition root)",
}


def _classify_layer(*, file_path: str, src_root: str) -> str | None:
    """Determine which architectural layer a file belongs to."""
    relative = str(Path(file_path).relative_to(src_root))
    for layer in LAYERS:
        if relative.startswith(f"{layer}/") or relative.startswith(f"{layer}\\"):
            return layer
    return None


def _is_composition_root(*, file_path: str, src_root: str) -> bool:
    """Check if a file is in the DI composition root (api/dependencies/)."""
    relative = str(Path(file_path).relative_to(src_root)).replace("\\", "/")
    return any(relative.startswith(pattern) for pattern in COMPOSITION_ROOT_PATTERNS)


def _extract_src_imports(*, tree: ast.AST) -> list[tuple[str, int]]:
    """Extract imports that reference architectural layers, as (target_layer, line)."""
    imports: list[tuple[str, int]] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                _check_module(module=alias.name, line=node.lineno, imports=imports)
        elif isinstance(node, ast.ImportFrom) and node.module:
            _check_module(module=node.module, line=node.lineno, imports=imports)

    return imports


def _check_module(
    *,
    module: str,
    line: int,
    imports: list[tuple[str, int]],
) -> None:
    """If a module path references one of the architectural layers, record it."""
    # Imports look like: mypkg.domain.models or domain.models. Strip an optional
    # top-level package prefix (anything that is not itself a layer name) before
    # classifying, so the check does not depend on the package's name.
    parts = module.split(".")
    target = parts[1] if parts[0] not in LAYERS and len(parts) > 1 else parts[0]

    if target in LAYERS:
        imports.append((target, line))


def _get_allowed_for_file(*, file_path: str, src_root: str, layer: str) -> set[str]:
    """Get the allowed import targets for a specific file, including exceptions."""
    allowed = ALLOWED_IMPORTS[layer].copy()

    # Composition root exception: api/dependencies/ may import infrastructure/
    # for DI wiring (binding ports to adapters at the composition root).
    if layer == "api" and _is_composition_root(file_path=file_path, src_root=src_root):
        allowed.add("infrastructure")

    return allowed


@dataclass
class LayerDepsCheck:
    """Validates hexagonal layer dependency rules."""

    name: str = "layer_deps"
    description: str = "Hexagonal architecture layer dependency validation"
    rules: list[str] = field(
        default_factory=lambda: [
            "LAYER-001: domain/ must not import from any other layer (pure Python only)",
            "LAYER-002: application/ can only import from domain/",
            "LAYER-003: infrastructure/ can only import from domain/ and application/",
            "LAYER-004: api/ can only import from domain/ and application/",
            "LAYER-005: only api/dependencies/ may import from infrastructure/ (composition root)",
        ]
    )

    def run(self, *, src_root: str) -> CheckResult:
        """Scan all Python files under the source root and validate import directions."""
        violations: list[Violation] = []
        warnings: list[Violation] = []
        src_path = Path(src_root)

        for py_file in sorted(src_path.rglob("*.py")):
            file_str = str(py_file)
            layer = _classify_layer(file_path=file_str, src_root=src_root)
            if layer is None:
                continue

            try:
                source = py_file.read_text(encoding="utf-8")
                tree = ast.parse(source, filename=file_str)
            except (OSError, UnicodeDecodeError, SyntaxError):
                warnings.append(
                    Violation(
                        file=str(py_file.relative_to(src_path)),
                        line=0,
                        rule="LAYER-000: parse error",
                        message=f"Could not parse {py_file.name} — skipping",
                        fix="Fix the syntax error first",
                    )
                )
                continue

            imports = _extract_src_imports(tree=tree)
            allowed = _get_allowed_for_file(file_path=file_str, src_root=src_root, layer=layer)
            is_comp_root = _is_composition_root(file_path=file_str, src_root=src_root)

            for target_layer, line in imports:
                if target_layer == layer:
                    continue

                if target_layer not in allowed:
                    relative_file = str(py_file.relative_to(src_path))

                    if layer == "api" and target_layer == "infrastructure" and not is_comp_root:
                        rule = RULE_MAP["api_composition"]
                        fix = (
                            "Move this import to api/dependencies/ (the composition root) "
                            "or depend on the port in application/ports/ instead"
                        )
                    else:
                        rule = RULE_MAP.get(layer, f"LAYER: {layer}/ cannot import {target_layer}/")
                        fix = _suggest_fix(source_layer=layer, target_layer=target_layer)

                    violations.append(
                        Violation(
                            file=relative_file,
                            line=line,
                            rule=rule,
                            message=f"{layer}/ imports from {target_layer}/",
                            fix=fix,
                        )
                    )

        status = Status.FAIL if violations else (Status.WARN if warnings else Status.PASS)
        return CheckResult(
            check=self.name,
            status=status,
            violations=violations,
            warnings=warnings,
        )


def _suggest_fix(*, source_layer: str, target_layer: str) -> str:
    """Generate a human-readable fix suggestion for a layer violation."""
    suggestions = {
        ("domain", "application"): "Domain must be pure — move the needed type to domain/",
        (
            "domain",
            "infrastructure",
        ): "Domain must be pure — define a port in application/ports/ instead",
        ("domain", "api"): "Domain must be pure — this dependency is inverted",
        (
            "application",
            "infrastructure",
        ): "Depend on a port (Protocol) in application/ports/, not the concrete implementation",
        (
            "application",
            "api",
        ): "Application must not know about the API layer — invert the dependency",
        (
            "api",
            "infrastructure",
        ): "Use dependency injection via api/dependencies/ instead of direct imports",
    }
    return suggestions.get(
        (source_layer, target_layer),
        f"Remove the import from {target_layer}/ — only allowed: {', '.join(ALLOWED_IMPORTS.get(source_layer, set()))}",
    )


# Self-register on import.
register(LayerDepsCheck())
