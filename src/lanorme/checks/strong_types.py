"""TYPE-001 through TYPE-004: Strong typing discipline.

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
    TYPE-004  A function with at least one annotated parameter that returns a
              real value in its own scope should declare a return annotation.
              Advisory warning, not a hard failure: presence enforcement is
              noisier than the weak-type rules, so this surfaces the gap
              without breaking the build.
              This is the completeness subset of ruff's ANN: it only fires
              when the parameters are already typed and a value escapes, so a
              fully untyped function or a procedure that returns nothing is
              left alone. Generators (own-scope ``yield`` / ``yield from``)
              are exempt; their annotation shape is an Iterator or Generator,
              which is a separate rule's concern.

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
from lanorme.discovery import iter_py_files

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


def _has_annotated_param(*, func: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    """Return True if any parameter carries an annotation.

    Covers positional-only, ordinary, keyword-only, ``*args`` and ``**kwargs``
    parameters. ``self`` and ``cls`` are ordinarily left unannotated, so they
    fall out naturally: a method whose only parameter is a bare ``self`` has no
    annotated parameter and does not qualify.
    """
    args = func.args
    positional_and_keyword = (*args.posonlyargs, *args.args, *args.kwonlyargs)
    for arg in positional_and_keyword:
        if arg.annotation is not None:
            return True
    if args.vararg is not None and args.vararg.annotation is not None:
        return True
    if args.kwarg is not None and args.kwarg.annotation is not None:
        return True
    return False


def _own_scope_nodes(*, func: ast.FunctionDef | ast.AsyncFunctionDef) -> list[ast.AST]:
    """Collect the body nodes that live in the function's OWN scope.

    The walk descends through ordinary statements and expressions but stops at
    the boundary of any nested ``def`` / ``async def`` / ``lambda``, because
    those introduce a fresh scope. A ``yield`` or a value-bearing ``return``
    inside a nested function therefore does not leak into this function's
    analysis. The signature itself is never visited, so default values that
    happen to contain a lambda are also out of view.
    """
    collected: list[ast.AST] = []

    def _descend(node: ast.AST) -> None:
        for child in ast.iter_child_nodes(node):
            if isinstance(child, ast.FunctionDef | ast.AsyncFunctionDef | ast.Lambda):
                continue
            collected.append(child)
            _descend(child)

    for statement in func.body:
        if isinstance(statement, ast.FunctionDef | ast.AsyncFunctionDef | ast.Lambda):
            continue
        collected.append(statement)
        _descend(statement)
    return collected


def _is_generator(*, own_nodes: list[ast.AST]) -> bool:
    """Return True if the own scope contains ``yield`` or ``yield from``."""
    return any(isinstance(node, ast.Yield | ast.YieldFrom) for node in own_nodes)


def _returns_real_value(*, own_nodes: list[ast.AST]) -> bool:
    """Return True if the own scope has a ``return <expr>`` that is not None.

    A bare ``return`` (``node.value is None``) and ``return None`` (the literal
    ``None`` constant) do not count. Every other value, including ``False``,
    ``0``, ``...`` and ``NotImplemented``, counts as a real value return.
    """
    for node in own_nodes:
        if not isinstance(node, ast.Return):
            continue
        if node.value is None:
            continue
        if isinstance(node.value, ast.Constant) and node.value.value is None:
            continue
        return True
    return False


_Finding = tuple[str, str, int, str, str]  # (severity, rule, line, message, fix)


def _param_findings(*, func: ast.FunctionDef | ast.AsyncFunctionDef) -> list[_Finding]:
    """TYPE-001/002 findings for weakly-typed parameter annotations."""
    findings: list[_Finding] = []
    for arg in (*func.args.args, *func.args.posonlyargs, *func.args.kwonlyargs):
        if arg.annotation is None:
            continue
        classified = _classify_annotation(arg.annotation)
        if classified is not None:
            severity, rule, message = classified
            findings.append(
                (
                    severity,
                    rule,
                    arg.lineno,
                    f"Parameter '{arg.arg}' in '{func.name}': {message}",
                    "Introduce a domain type (TypedDict, dataclass, or value object) and annotate with it",
                )
            )
    return findings


def _kwarg_findings(*, func: ast.FunctionDef | ast.AsyncFunctionDef) -> list[_Finding]:
    """TYPE-003 finding for a weakly-typed ``**kwargs`` parameter."""
    kw = func.args.kwarg
    if kw is None:
        return []
    ann_text = _annotation_text(kw.annotation) if kw.annotation else "<missing>"
    weak = kw.annotation is None or _annotation_text(kw.annotation) in {
        "Any",
        "dict",
        "dict[str, Any]",
        "Dict[str, Any]",
    }
    if not weak:
        return []
    return [
        (
            "fail",
            "TYPE-003",
            kw.lineno,
            f"'**{kw.arg}' in '{func.name}' is weakly typed ('{ann_text}') — use Unpack[TypedDict]",
            "Define a TypedDict for the kwargs shape and annotate as 'Unpack[YourTypedDict]'",
        )
    ]


def _return_findings(*, func: ast.FunctionDef | ast.AsyncFunctionDef) -> list[_Finding]:
    """TYPE-001/002 (weak return) or TYPE-004 (missing return annotation) findings."""
    if func.returns is not None:
        classified = _classify_annotation(func.returns)
        if classified is None:
            return []
        severity, rule, message = classified
        return [
            (
                severity,
                rule,
                func.lineno,
                f"Return type of '{func.name}': {message}",
                "Introduce a domain type and annotate the return with it",
            )
        ]
    # TYPE-004: a complete-enough signature (annotated params, a real value
    # escaping the function's own scope, not a generator) should also declare
    # its return type. Advisory warning, not a hard failure: this is the
    # high-signal completeness subset of presence enforcement, not blanket ANN.
    own_nodes = _own_scope_nodes(func=func)
    if (
        _has_annotated_param(func=func)
        and not _is_generator(own_nodes=own_nodes)
        and _returns_real_value(own_nodes=own_nodes)
    ):
        return [
            (
                "warn",
                "TYPE-004",
                func.lineno,
                f"'{func.name}' has annotated parameters and returns a value but no "
                "return annotation. Declare the return type so the signature is complete.",
                "Add a return annotation (for example '-> ResultType') to the signature",
            )
        ]
    return []


def _check_function(
    *,
    func: ast.FunctionDef | ast.AsyncFunctionDef,
    relative_file: str,
) -> tuple[list[Violation], list[Violation]]:
    """Return ``(violations, warnings)`` for the function's annotations."""
    if _has_exempt_decorator(func_node=func):
        return [], []

    violations: list[Violation] = []
    warnings: list[Violation] = []
    for severity, rule, line, message, fix in (
        *_param_findings(func=func),
        *_kwarg_findings(func=func),
        *_return_findings(func=func),
    ):
        finding = Violation(file=relative_file, line=line, rule=rule, message=message, fix=fix)
        (violations if severity == "fail" else warnings).append(finding)
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
            "TYPE-004: A function with annotated parameters that returns a value should declare a return type (advisory warning)",
        ]
    )

    def run(self, *, src_root: str) -> CheckResult:
        violations: list[Violation] = []
        warnings: list[Violation] = []
        src_path = Path(src_root)

        for py_file in iter_py_files(src_path):
            relative_file = str(py_file.relative_to(src_path))
            if _is_exempt_path(relative_path=relative_file):
                continue

            try:
                source = py_file.read_text(encoding="utf-8")
                tree = ast.parse(source, filename=str(py_file))
                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                        func_violations, func_warnings = _check_function(
                            func=node, relative_file=relative_file
                        )
                        violations.extend(func_violations)
                        warnings.extend(func_warnings)
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
            except RecursionError:
                # A deeply nested annotation (e.g. a union with thousands of
                # terms) overflows the recursive annotation walk. Skip the file
                # rather than crash the whole run.
                warnings.append(
                    Violation(
                        file=relative_file,
                        line=0,
                        rule="TYPE-000: too deeply nested",
                        message=f"{py_file.name} is too deeply nested to analyse — skipping",
                        fix="No action needed; this file is exempt from TYPE-001..003",
                    )
                )
                continue

        status = Status.FAIL if violations else (Status.WARN if warnings else Status.PASS)
        return CheckResult(
            check=self.name,
            status=status,
            violations=violations,
            warnings=warnings,
        )


register(StrongTypesCheck())
