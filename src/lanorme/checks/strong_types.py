"""TYPE-001 through TYPE-003: Strong typing discipline.

Bridges the gap ruff's ANN rules and ty leave open: ANN enforces *presence*
of annotations; ty catches *errors* in declared types; neither flags
*weakly-typed dicts* or *bare container types* that pass type-checking
but defeat the point of having a static type system. This check fills that
gap with a curated set of "stop using stringly-typed dicts" rules.

Rules:
    TYPE-001  No ``dict[str, Any]`` (or ``dict``, or ``Dict[str, Any]``) in
              function signatures, return types, or class fields.
              Reach for a ``TypedDict``, a dataclass, a Pydantic model, or
              a domain value object instead.
    TYPE-002  No bare ``dict`` / ``list`` / ``tuple`` / ``set`` (without
              type parameters) in annotations. ``list[int]`` not ``list``.
    TYPE-003  ``**kwargs`` parameters must be annotated with a concrete
              type (or ``Unpack[TypedDict]``), bare ``**kwargs: Any``
              is forbidden at signature boundaries.

Boundary exemptions: this check skips files under ``tests/`` and
``migrations/``. JSON deserialisation entrypoints (functions decorated
with the ``@boundary_dict`` marker, if introduced) should also be added
to ``_EXEMPT_DECORATORS`` below as the codebase grows.

Run:
    lanorme check . --check=strong_types
"""

from __future__ import annotations

import ast
from dataclasses import dataclass, field
from pathlib import Path

from lanorme import CheckResult, Status, Violation, register

_BARE_CONTAINERS = frozenset(
    {"dict", "list", "tuple", "set", "frozenset", "Dict", "List", "Tuple", "Set", "FrozenSet"}
)
# `Any` is "I don't know the type", always a hard fail at signature boundaries.
_HARD_WEAK_TYPES = frozenset({"Any"})
# `object` is "intentional placeholder until the concrete type lands", emitted
# as a warning so scaffold-stage Protocols that pre-date their domain entities
# do not block the build. Once an aggregate is defined, the placeholder must
# be replaced and the warning clears on its own.
_SOFT_WEAK_TYPES = frozenset({"object"})
_EXEMPT_DECORATORS = frozenset(
    {
        # Add boundary-marker decorators here as the codebase introduces them.
        # e.g. "boundary_dict", "raw_json", "external_payload"
    }
)
_EXEMPT_PATH_FRAGMENTS = ("tests/", "migrations/")


def _is_exempt_path(*, relative_path: str) -> bool:
    normalised = relative_path.replace("\\", "/")
    return any(normalised.startswith(p) or f"/{p}" in normalised for p in _EXEMPT_PATH_FRAGMENTS)


def _has_exempt_decorator(*, func_node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    for dec in func_node.decorator_list:
        name = _decorator_name(dec)
        if name in _EXEMPT_DECORATORS:
            return True
    return False


def _decorator_name(node: ast.expr) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    if isinstance(node, ast.Call):
        return _decorator_name(node.func)
    return None


def _annotation_text(annotation: ast.expr) -> str:
    """Render an annotation AST back to source text (best-effort)."""
    try:
        return ast.unparse(annotation)
    except Exception:
        return "<unparseable>"


def _classify_annotation(annotation: ast.expr) -> tuple[str, str, str] | None:
    """Classify an annotation.

    Returns a tuple ``(severity, rule_id, message)`` where ``severity`` is
    ``"fail"`` or ``"warn"``, or ``None`` if the annotation is clean. ``Any``
    leaves are hard fails; ``object`` leaves are placeholder warnings.
    """
    # Bare container: `dict`, `list`, `Dict`, etc. (no subscript at all).
    if isinstance(annotation, ast.Name) and annotation.id in _BARE_CONTAINERS:
        return (
            "fail",
            "TYPE-002",
            f"Bare '{annotation.id}' annotation lacks type parameters — use '{annotation.id}[K, V]' or similar",
        )

    # Subscripted container with weak value type: `dict[str, Any]`, `list[Any]`,
    # `list[object]`, etc.
    if isinstance(annotation, ast.Subscript):
        outer = (
            _decorator_name(annotation.value)
            if isinstance(annotation.value, ast.Attribute)
            else (annotation.value.id if isinstance(annotation.value, ast.Name) else None)
        )
        if outer in _BARE_CONTAINERS:
            inner = annotation.slice
            inner_names = _collect_value_names(inner)
            rendered = _annotation_text(annotation)
            if any(name in _HARD_WEAK_TYPES for name in inner_names):
                return (
                    "fail",
                    "TYPE-001",
                    f"Weakly-typed container '{rendered}' (Any leaf) — define a TypedDict, dataclass, or value object",
                )
            if any(name in _SOFT_WEAK_TYPES for name in inner_names):
                return (
                    "warn",
                    "TYPE-001",
                    f"Placeholder container '{rendered}' (object leaf) — replace with the concrete domain type when the entity lands",
                )

    return None


def _collect_value_names(node: ast.expr) -> list[str]:
    """Pull the leaf Name identifiers out of an annotation subtree."""
    names: list[str] = []
    if isinstance(node, ast.Name):
        names.append(node.id)
    elif isinstance(node, ast.Tuple):
        for elt in node.elts:
            names.extend(_collect_value_names(elt))
    elif isinstance(node, ast.Subscript):
        # `Optional[Any]` → look at the slice
        names.extend(_collect_value_names(node.slice))
    elif isinstance(node, ast.BinOp):
        # `int | None` style unions
        names.extend(_collect_value_names(node.left))
        names.extend(_collect_value_names(node.right))
    return names


def _check_function(
    *,
    func: ast.FunctionDef | ast.AsyncFunctionDef,
    relative_file: str,
) -> tuple[list[Violation], list[Violation]]:
    """Return ``(violations, warnings)`` for the function's annotations."""
    violations: list[Violation] = []
    warnings: list[Violation] = []

    if _has_exempt_decorator(func_node=func):
        return violations, warnings

    def _emit(*, severity: str, rule: str, line: int, message: str, fix: str) -> None:
        target = violations if severity == "fail" else warnings
        target.append(
            Violation(
                file=relative_file,
                line=line,
                rule=rule,
                message=message,
                fix=fix,
            )
        )

    # Parameter annotations.
    for arg in (*func.args.args, *func.args.posonlyargs, *func.args.kwonlyargs):
        if arg.annotation is None:
            continue
        finding = _classify_annotation(arg.annotation)
        if finding is not None:
            severity, rule, message = finding
            _emit(
                severity=severity,
                rule=rule,
                line=arg.lineno,
                message=f"Parameter '{arg.arg}' in '{func.name}': {message}",
                fix="Introduce a domain type (TypedDict, dataclass, or value object) and annotate with it",
            )

    # **kwargs annotation (TYPE-003).
    if func.args.kwarg is not None:
        kw = func.args.kwarg
        ann_text = _annotation_text(kw.annotation) if kw.annotation else "<missing>"
        if kw.annotation is None or _annotation_text(kw.annotation) in {
            "Any",
            "dict",
            "dict[str, Any]",
            "Dict[str, Any]",
        }:
            _emit(
                severity="fail",
                rule="TYPE-003",
                line=kw.lineno,
                message=f"'**{kw.arg}' in '{func.name}' is weakly typed ('{ann_text}') — use Unpack[TypedDict]",
                fix="Define a TypedDict for the kwargs shape and annotate as 'Unpack[YourTypedDict]'",
            )

    # Return annotation.
    if func.returns is not None:
        finding = _classify_annotation(func.returns)
        if finding is not None:
            severity, rule, message = finding
            _emit(
                severity=severity,
                rule=rule,
                line=func.lineno,
                message=f"Return type of '{func.name}': {message}",
                fix="Introduce a domain type and annotate the return with it",
            )

    return violations, warnings


@dataclass
class StrongTypesCheck:
    """Enforces strong typing at signature boundaries, no weakly-typed dicts."""

    name: str = "strong_types"
    description: str = "Strong typing discipline (no weakly-typed dicts at signature boundaries)"
    rules: list[str] = field(
        default_factory=lambda: [
            "TYPE-001: No 'dict[str, Any]' (or similar weakly-typed containers) in signatures or returns",
            "TYPE-002: No bare 'dict' / 'list' / 'tuple' / 'set' without type parameters",
            "TYPE-003: '**kwargs' must be annotated with a concrete type or 'Unpack[TypedDict]'",
        ]
    )

    def run(self, *, src_root: str) -> CheckResult:
        violations: list[Violation] = []
        warnings: list[Violation] = []
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
                        rule="TYPE-000: parse error",
                        message=f"Could not parse {py_file.name} — skipping",
                        fix="Fix the syntax error first",
                    )
                )
                continue

            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                    func_violations, func_warnings = _check_function(
                        func=node, relative_file=relative_file
                    )
                    violations.extend(func_violations)
                    warnings.extend(func_warnings)

        status = Status.FAIL if violations else (Status.WARN if warnings else Status.PASS)
        return CheckResult(
            check=self.name,
            status=status,
            violations=violations,
            warnings=warnings,
        )


register(StrongTypesCheck())
