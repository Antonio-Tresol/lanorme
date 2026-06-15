"""CMT-005: comments that restate the next line of code (experimental).

A precision-funnel detector that flags one-line comments which paraphrase the
``what`` of the adjacent statement without adding any ``why`` / caveat /
unit / reference / non-obvious context. The design (``docs/cmt005-design.md``)
is precision-first by construction: 11-category allowlist, AST adjacency,
stem-equality, a hand-curated verb-to-AST-node predicate table, an
asymmetric coverage floor of 1.0, and a content-word cap.

Measured against ``evals/corpora/comments_restating/`` (167 labels):
**P = 1.000 / R = 0.418 / F1 = 0.589**. The recall is bounded by the
design's refusal to chase synonym paraphrases without losing precision;
the metric is the headline.

Default-off (experimental). Opt in via::

    [tool.lanorme.restating]
    enabled = true

Run:
    lanorme check . --check=restating
"""

from __future__ import annotations

import ast
import io
import re
import tokenize
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from lanorme import CheckResult, Status, Violation, register
from lanorme.discovery import iter_py_files

MAX_CONTENT_WORDS = 4
MIN_STEM_LEN = 4
COVERAGE_FLOOR = 1.0
ALLOW_TRAILING = True

_PRAGMA_PREFIXES = (
    "noqa", "type:", "pragma", "pylint:", "mypy:", "ruff:", "isort:", "fmt:",
    "!", "-*-", "region", "endregion",
)

_STOPWORDS = frozenset({
    "the", "a", "an", "to", "of", "and", "or", "for", "in", "on", "is", "be",
    "this", "that", "it", "with", "by", "as", "at", "from", "into", "are",
    "was", "were", "we", "you", "they", "its", "any", "all", "some",
})

_ALLOWLIST_TAGS = frozenset(
    {"todo", "fixme", "xxx", "hack", "note", "bug", "review", "warning", "optimize", "deprecated"}
)
_ALLOWLIST_PHRASES: tuple[str, ...] = (
    "so that", "so we", "in order to", "to avoid", "to prevent", "on purpose",
    "due to", "caused by", "that's why", "which is why", "work around",
    "do not", "don't", "must ", "must not", "not thread", "side effect", "in place",
    "(c)", "all rights reserved", "mit license",
    "http://", "https://", "www.", "see ", "see:", "cf.", "ref:", "ref ", "refs ",
    "per ", "pep ", "pep-", "bug #", "issue #", "gh-",
    "e.g.", "i.e.", "eg.", "for example", "for instance", "example:", "examples:", "such as",
    ":param", ":type", ":returns", ":return:", ":rtype", ":raises",
    "args:", "returns:", "raises:", "yields:", "params:", "usage:",
    "public:", "internal:",
    "0-based", "1-based", "zero-based", "one-based", "null-terminated",
)
_ALLOWLIST_WORD_RE = re.compile(
    r"\b(?:"
    "because|since|otherwise|prevent|ensure|workaround|reason|intentionally|"
    "careful|caution|danger|gotcha|never|always|beware|unsafe|mutate|assumes|"
    "assumption|requires|precondition|invariant|"
    "copyright|license|licence|spdx|gnu|apache|bsd|gpl|"
    "rfc|deprecated|inclusive|exclusive|utc|seconds|ms|bytes|index|offset|nul"
    r")\b",
    re.IGNORECASE,
)
_SECTION_HEADER_DASH = re.compile(r"^[-=#*~ ]{2,}$")
_NUMERIC_REF = re.compile(r"#\d+")
_CAMEL_SPLIT = re.compile(r"[A-Z]+(?=[A-Z][a-z])|[A-Z]?[a-z]+|[A-Z]+|[0-9]+")
_WORD = re.compile(r"[A-Za-z]+")

_STMT_KEYWORD: dict[type, str] = {
    ast.Return: "return", ast.Delete: "del", ast.Assert: "assert", ast.Raise: "raise",
    ast.Import: "import", ast.ImportFrom: "import",
    ast.For: "for", ast.AsyncFor: "for", ast.While: "while",
}

_SKIP_DIRS = frozenset({".git", ".venv", "venv", "node_modules", "__pycache__", "dist", "build"})


def _split_identifier(*, name: str) -> list[str]:
    out: list[str] = []
    for part in re.split(r"_+", name):
        out.extend(_CAMEL_SPLIT.findall(part))
    return [token.lower() for token in out if token]


def _stem(*, word: str) -> str:
    for suffix in ("ing", "tion", "ies", "es", "ed", "er", "s"):
        if word.endswith(suffix) and len(word) - len(suffix) >= MIN_STEM_LEN:
            return word[: -len(suffix)]
    return word


def _is_augassign(*, op_type: type) -> Callable[[ast.stmt], bool]:
    return lambda s: isinstance(s, ast.AugAssign) and isinstance(s.op, op_type)


def _is_node_type(*, types: tuple[type, ...]) -> Callable[[ast.stmt], bool]:
    return lambda s: isinstance(s, types)


def _contains_yield(s: ast.stmt) -> bool:
    return any(isinstance(node, (ast.Yield, ast.YieldFrom)) for node in ast.walk(s))


def _is_expr_call(s: ast.stmt) -> bool:
    return isinstance(s, ast.Expr) and isinstance(s.value, ast.Call)


def _is_print_like(s: ast.stmt) -> bool:
    if not isinstance(s, ast.Expr) or not isinstance(s.value, ast.Call):
        return False
    func = s.value.func
    name = func.id if isinstance(func, ast.Name) else (func.attr if isinstance(func, ast.Attribute) else "")
    return name == "print" or name.startswith("log")


_VERB_TABLE: dict[str, Callable[[ast.stmt], bool]] = {
    **dict.fromkeys(("increment", "inc", "bump"), _is_augassign(op_type=ast.Add)),
    **dict.fromkeys(("decrement", "dec", "subtract"), _is_augassign(op_type=ast.Sub)),
    **dict.fromkeys(("return", "returns"), _is_node_type(types=(ast.Return,))),
    **dict.fromkeys(("yield", "yields"), _contains_yield),
    **dict.fromkeys(("raise", "throw", "throws"), _is_node_type(types=(ast.Raise,))),
    **dict.fromkeys(("import", "imports"), _is_node_type(types=(ast.Import, ast.ImportFrom))),
    **dict.fromkeys(("loop", "iterate", "iterates", "iterating"), _is_node_type(types=(ast.For, ast.AsyncFor, ast.While))),
    **dict.fromkeys(("assign", "set", "store"), _is_node_type(types=(ast.Assign, ast.AnnAssign))),
    **dict.fromkeys(("delete", "del", "remove"), _is_node_type(types=(ast.Delete,))),
    **dict.fromkeys(("assert", "check", "verify"), _is_node_type(types=(ast.Assert,))),
    **dict.fromkeys(("call", "invoke"), _is_expr_call),
    **dict.fromkeys(("print", "log"), _is_print_like),
}


def _is_section_header(text: str) -> bool:
    stripped = text.strip()
    if _SECTION_HEADER_DASH.fullmatch(stripped):
        return True
    words = stripped.split()
    return len(words) >= 2 and all(word.isupper() and len(word) >= 2 for word in words)


def _is_allowlisted(*, text: str, low: str) -> bool:
    if low.startswith(_PRAGMA_PREFIXES):
        return True
    first = (low.split() or [""])[0].rstrip(":")
    if first in _ALLOWLIST_TAGS:
        return True
    if any(phrase in low for phrase in _ALLOWLIST_PHRASES):
        return True
    if _ALLOWLIST_WORD_RE.search(low):
        return True
    if _is_section_header(text):
        return True
    return bool(_NUMERIC_REF.search(low))


def _build_stmt_index(*, tree: ast.Module) -> dict[int, ast.stmt]:
    index: dict[int, ast.stmt] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.stmt):
            index.setdefault(node.lineno, node)
    return index


def _is_simple_statement(*, s: ast.stmt) -> bool:
    if isinstance(s, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
        return False
    if getattr(s, "decorator_list", None):
        return False
    return isinstance(
        s,
        (
            ast.Assign, ast.AnnAssign, ast.AugAssign, ast.Return, ast.Delete,
            ast.Raise, ast.Assert, ast.Import, ast.ImportFrom,
            ast.For, ast.AsyncFor, ast.While, ast.Expr,
        ),
    )


def _code_tokens(*, s: ast.stmt) -> set[str]:
    raw: set[str] = set()
    for node in ast.walk(s):
        if isinstance(node, ast.Name):
            raw.update(_split_identifier(name=node.id))
        elif isinstance(node, ast.Attribute):
            raw.update(_split_identifier(name=node.attr))
        elif isinstance(node, ast.arg):
            raw.update(_split_identifier(name=node.arg))
        elif isinstance(node, ast.keyword) and node.arg:
            raw.update(_split_identifier(name=node.arg))
    keyword = _STMT_KEYWORD.get(type(s))
    if keyword:
        raw.add(keyword)
    return {_stem(word=token) for token in raw if token}


@dataclass(frozen=True)
class _Comment:
    line: int
    text: str
    standalone: bool


@dataclass(frozen=True)
class _Context:
    stmt_index: dict[int, ast.stmt]
    stmt_lines: list[int]
    standalone_lines: set[int]


def _adjacent_statement(*, comment: _Comment, ctx: _Context) -> ast.stmt | None:
    if comment.standalone:
        for line in ctx.stmt_lines:
            if line > comment.line:
                return ctx.stmt_index[line]
        return None
    return ctx.stmt_index.get(comment.line)


def _restates(*, comment: _Comment, s: ast.stmt) -> bool:
    text = comment.text
    low = text.lower()
    if _is_allowlisted(text=text, low=low):
        return False
    words = [w for w in _WORD.findall(low) if w not in _STOPWORDS]
    if not words or len(words) > MAX_CONTENT_WORDS:
        return False
    verbs = [w for w in words if w in _VERB_TABLE]
    content = [w for w in words if w not in _VERB_TABLE]
    code = _code_tokens(s=s)
    covered_w = sum(1 for w in content if _stem(word=w) in code)
    covered_v = sum(1 for v in verbs if _VERB_TABLE[v](s))
    total = len(content) + len(verbs)
    return total > 0 and (covered_w + covered_v) / total >= COVERAGE_FLOOR


def _collect_comments(*, source: str, source_lines: list[str]) -> list[_Comment]:
    comments: list[_Comment] = []
    try:
        for token in tokenize.generate_tokens(io.StringIO(source).readline):
            if token.type != tokenize.COMMENT:
                continue
            row, col = token.start
            before = source_lines[row - 1][:col] if 0 <= row - 1 < len(source_lines) else ""
            comments.append(
                _Comment(line=row, text=token.string.lstrip("#").strip(), standalone=not before.strip())
            )
    except (tokenize.TokenError, IndentationError, SyntaxError):
        pass
    return comments


def _restating_violations(*, tree: ast.Module, comments: list[_Comment], file: str) -> list[Violation]:
    stmt_index = _build_stmt_index(tree=tree)
    ctx = _Context(
        stmt_index=stmt_index,
        stmt_lines=sorted(stmt_index),
        standalone_lines={c.line for c in comments if c.standalone},
    )
    found: list[Violation] = []
    for comment in comments:
        if comment.standalone and (
            (comment.line - 1) in ctx.standalone_lines or (comment.line + 1) in ctx.standalone_lines
        ):
            continue
        if not comment.standalone and not ALLOW_TRAILING:
            continue
        s = _adjacent_statement(comment=comment, ctx=ctx)
        if s is None or not _is_simple_statement(s=s):
            continue
        if _restates(comment=comment, s=s):
            found.append(
                Violation(
                    file=file,
                    line=comment.line,
                    rule="CMT-005",
                    message=f"Comment restates the code: {comment.text[:50]}",
                    fix="Remove it, or explain the why rather than the what",
                )
            )
    return found


@dataclass
class RestatingCheck:
    """CMT-005: flag comments that restate the next line of code (experimental, opt-in)."""

    name: str = "restating"
    description: str = "Comments that restate the next line of code (CMT-005, experimental)"
    enabled: bool = False
    rules: list[str] = field(
        default_factory=lambda: [
            "CMT-005: No comments that restate the next line of code (experimental)",
        ]
    )

    def configure(self, *, settings: dict[str, bool]) -> None:
        """Apply ``[tool.lanorme.restating]`` configuration."""
        if "enabled" in settings:
            self.enabled = bool(settings["enabled"])

    def run(self, *, src_root: str) -> CheckResult:
        if not self.enabled:
            return CheckResult(check=self.name, status=Status.PASS, violations=[])
        violations: list[Violation] = []
        root = Path(src_root)
        for path in iter_py_files(root):
            if any(part in _SKIP_DIRS for part in path.parts):
                continue
            try:
                source = path.read_text(encoding="utf-8")
                tree = ast.parse(source, filename=str(path))
            except (OSError, UnicodeDecodeError, SyntaxError):
                continue
            relative = str(path.relative_to(root))
            source_lines = source.splitlines()
            comments = _collect_comments(source=source, source_lines=source_lines)
            violations.extend(_restating_violations(tree=tree, comments=comments, file=relative))
        status = Status.FAIL if violations else Status.PASS
        return CheckResult(check=self.name, status=status, violations=violations)


register(RestatingCheck())
