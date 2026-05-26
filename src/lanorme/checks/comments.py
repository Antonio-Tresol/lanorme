"""CMT-001 through CMT-005: concise, clean comments in Python source.

Selectable rules for the quality of ``#`` comments (and, for the style rules,
docstrings):

    CMT-001  No commented-out code.
    CMT-002  No verbose comments (block too long, or line too long).
    CMT-003  No em dashes in comments or docstrings.
    CMT-004  No emoji in comments or docstrings.
    CMT-005  No comments that merely restate the next line of code (EXPERIMENTAL:
             a robust, well-tested detector is under development; the current
             heuristic is a placeholder and is off by default).

CMT-001 and CMT-002 are hygiene and run by default. CMT-003, CMT-004 and
CMT-005 are stylistic or heuristic and stay off until enabled::

    [tool.lanorme.comments]
    em_dash = true
    emoji = true
    restating = true
    max_block_lines = 6
    max_comment_chars = 120

Run:
    lanorme check . --check=comments
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

_EM_DASH = "—"

_EMOJI = re.compile(
    "["
    "\U0001f300-\U0001faff"
    "\U00002600-\U000026ff"
    "\U00002700-\U000027bf"
    "\U0001f1e6-\U0001f1ff"
    "\U00002b00-\U00002bff"
    "\U0000fe0f"
    "\U0000200d"
    "]"
)

_SKIP_DIRS = frozenset({".git", ".venv", "venv", "node_modules", "__pycache__", "dist", "build"})

# Comment text starting with one of these is tooling, not prose or code.
_PRAGMA_PREFIXES = (
    "noqa",
    "type:",
    "pragma",
    "pylint:",
    "mypy:",
    "ruff:",
    "isort:",
    "fmt:",
    "!",
    "-*-",
    "region",
    "endregion",
)

# Statement node types that mark a comment as commented-out code.
_CODE_NODES = (
    ast.Import,
    ast.ImportFrom,
    ast.Assign,
    ast.AnnAssign,
    ast.AugAssign,
    ast.FunctionDef,
    ast.AsyncFunctionDef,
    ast.ClassDef,
    ast.For,
    ast.While,
    ast.With,
    ast.Delete,
    ast.Raise,
    ast.Assert,
)

_STOPWORDS = frozenset(
    {
        "the", "a", "an", "to", "of", "and", "or", "for", "in", "on", "is", "be",
        "this", "that", "it", "with", "by", "as", "at", "from", "into", "are",
        "was", "were", "we", "you", "they", "its", "any", "all", "some",
    }
)
_WORD = re.compile(r"[A-Za-z]+")


# --- CMT-005: restating-comment detector (see docs/cmt005-design.md) ---

MAX_CONTENT_WORDS = 4
MIN_STEM_LEN = 4
COVERAGE_FLOOR = 1.0
ALLOW_TRAILING = True

# Allowlist: any of these signals exempts a comment from CMT-005 scoring.
_ALLOWLIST_TAGS = frozenset(
    {"todo", "fixme", "xxx", "hack", "note", "bug", "review", "warning", "optimize", "deprecated"}
)
# Phrases: entries with spaces or non-word chars; safe to match via `in`.
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
# Single words: must match as whole words, never as substrings (a literal "ms"
# inside "items" must not exempt the comment).
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

# Hard keyword introduced by each simple-statement node type.
_STMT_KEYWORD: dict[type, str] = {
    ast.Return: "return", ast.Delete: "del", ast.Assert: "assert", ast.Raise: "raise",
    ast.Import: "import", ast.ImportFrom: "import",
    ast.For: "for", ast.AsyncFor: "for", ast.While: "while",
}


def _split_identifier(*, name: str) -> list[str]:
    """Split snake_case / camelCase / PascalCase into lowercase word tokens."""
    out: list[str] = []
    for part in re.split(r"_+", name):
        out.extend(_CAMEL_SPLIT.findall(part))
    return [token.lower() for token in out if token]


def _stem(*, word: str) -> str:
    """Trim one common English suffix iff the residue is long enough; never below MIN_STEM_LEN."""
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


# Verb -> predicate on the adjacent statement node. Hand-curated; small on purpose.
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
    """First top-level statement starting at each line number."""
    index: dict[int, ast.stmt] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.stmt):
            index.setdefault(node.lineno, node)
    return index


def _is_simple_statement(*, s: ast.stmt) -> bool:
    """Statements that a one-line restating comment could plausibly paraphrase."""
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
    """Stemmed identifier + keyword tokens from a statement. Literals excluded on purpose."""
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
class _RestatingContext:
    stmt_index: dict[int, ast.stmt]
    stmt_lines: list[int]
    standalone_lines: set[int]


def _adjacent_statement(*, comment: "_Comment", ctx: _RestatingContext) -> ast.stmt | None:
    if comment.standalone:
        for line in ctx.stmt_lines:
            if line > comment.line:
                return ctx.stmt_index[line]
        return None
    return ctx.stmt_index.get(comment.line)


def _in_comment_block(*, comment: "_Comment", standalone_lines: set[int]) -> bool:
    return (comment.line - 1) in standalone_lines or (comment.line + 1) in standalone_lines


def _restates_v2(*, comment: "_Comment", s: ast.stmt) -> bool:
    text = comment.text
    low = text.lower()
    if _is_allowlisted(text=text, low=low):
        return False
    words = [w for w in _WORD.findall(low) if w not in _STOPWORDS]
    if not words or len(words) > MAX_CONTENT_WORDS:
        return False
    verbs = [w for w in words if w in _VERB_TABLE]
    content = [w for w in words if w not in _VERB_TABLE]
    code_tokens = _code_tokens(s=s)
    covered_w = sum(1 for w in content if _stem(word=w) in code_tokens)
    covered_v = sum(1 for v in verbs if _VERB_TABLE[v](s))
    total = len(content) + len(verbs)
    return total > 0 and (covered_w + covered_v) / total >= COVERAGE_FLOOR


@dataclass(frozen=True)
class _Comment:
    line: int
    text: str
    standalone: bool


def _collect_comments(*, source: str, source_lines: list[str]) -> list[_Comment]:
    """Return every ``#`` comment via tokenize (so ``#`` inside strings is ignored)."""
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


def _docstring_lines(*, tree: ast.Module) -> list[tuple[int, str]]:
    """Return (line, text) for each line of every module/class/function docstring."""
    out: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Module | ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef):
            continue
        doc = ast.get_docstring(node, clean=False)
        if doc is None or not node.body:
            continue
        start = node.body[0].lineno
        for offset, text in enumerate(doc.splitlines()):
            out.append((start + offset, text))
    return out


def _has_ellipsis_arg(*, call: ast.Call) -> bool:
    return any(isinstance(arg, ast.Constant) and arg.value is Ellipsis for arg in call.args)


def _looks_like_code(*, text: str) -> bool:
    """True if a comment body parses as a code statement rather than prose."""
    if not text or text.startswith(_PRAGMA_PREFIXES) or text.endswith((".", "?", "!", ":")):
        return False
    try:
        tree = ast.parse(text)
    except (SyntaxError, ValueError):
        return False
    for node in tree.body:
        # 'label: type' without a value reads as documentation, not an assignment.
        if isinstance(node, ast.AnnAssign) and node.value is None:
            continue
        # 'foo(...)' with a literal ellipsis is illustrative, not dead code.
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
            if not _has_ellipsis_arg(call=node.value):
                return True
            continue
        if isinstance(node, _CODE_NODES):
            return True
    return False


def _violation(*, relative_file: str, line: int, code: str, message: str, fix: str) -> Violation:
    return Violation(file=relative_file, line=line, rule=code, message=message, fix=fix)


@dataclass
class CommentsCheck:
    """Concise, clean comments: commented-out code, verbosity, style, restating."""

    name: str = "comments"
    description: str = "Concise, clean comments (commented-out code, verbosity, style)"
    flag_commented_code: bool = True
    flag_verbose: bool = True
    flag_em_dash: bool = False
    flag_emoji: bool = False
    flag_restating: bool = False
    max_block_lines: int = 6
    max_comment_chars: int = 120
    rules: list[str] = field(
        default_factory=lambda: [
            "CMT-001: No commented-out code",
            "CMT-002: No verbose comments (block or line too long)",
            "CMT-003: No em dashes in comments or docstrings",
            "CMT-004: No emoji in comments or docstrings",
            "CMT-005: No comments that restate the next line of code (experimental)",
        ]
    )

    def configure(self, *, settings: dict[str, bool | int]) -> None:
        """Apply ``[tool.lanorme.comments]`` configuration."""
        for key in ("flag_commented_code", "flag_verbose"):
            short = key.removeprefix("flag_")
            if short in settings:
                setattr(self, key, bool(settings[short]))
        for short in ("em_dash", "emoji", "restating"):
            if short in settings:
                setattr(self, f"flag_{short}", bool(settings[short]))
        for key in ("max_block_lines", "max_comment_chars"):
            if key in settings:
                setattr(self, key, int(settings[key]))

    def _style_violations(self, *, text: str, line: int, relative_file: str) -> list[Violation]:
        found: list[Violation] = []
        if self.flag_em_dash and _EM_DASH in text:
            found.append(
                _violation(
                    relative_file=relative_file,
                    line=line,
                    code="CMT-003",
                    message="Em dash in comment/docstring",
                    fix="Rewrite with a comma, parentheses, or a full stop",
                )
            )
        if self.flag_emoji and _EMOJI.search(text):
            found.append(
                _violation(
                    relative_file=relative_file,
                    line=line,
                    code="CMT-004",
                    message="Emoji in comment/docstring",
                    fix="Remove the emoji",
                )
            )
        return found

    def _verbose_violations(self, *, comments: list[_Comment], relative_file: str) -> list[Violation]:
        found: list[Violation] = []
        for comment in comments:
            if len(comment.text) > self.max_comment_chars:
                found.append(
                    _violation(
                        relative_file=relative_file,
                        line=comment.line,
                        code="CMT-002",
                        message=f"Comment line is {len(comment.text)} chars (limit {self.max_comment_chars})",
                        fix="Tighten it, or move the detail into a docstring",
                    )
                )
        found.extend(self._block_violations(comments=comments, relative_file=relative_file))
        return found

    def _block_violations(self, *, comments: list[_Comment], relative_file: str) -> list[Violation]:
        found: list[Violation] = []
        standalone = [c for c in comments if c.standalone]
        index = 0
        while index < len(standalone):
            end = index
            while end + 1 < len(standalone) and standalone[end + 1].line == standalone[end].line + 1:
                end += 1
            length = end - index + 1
            if length > self.max_block_lines:
                found.append(
                    _violation(
                        relative_file=relative_file,
                        line=standalone[index].line,
                        code="CMT-002",
                        message=f"Comment block is {length} lines (limit {self.max_block_lines})",
                        fix="Tighten it, or move the detail into a docstring",
                    )
                )
            index = end + 1
        return found

    def _scan_file(
        self,
        *,
        tree: ast.Module,
        comments: list[_Comment],
        source_lines: list[str],
        relative_file: str,
    ) -> list[Violation]:
        found: list[Violation] = []
        if self.flag_commented_code:
            found.extend(
                _violation(
                    relative_file=relative_file,
                    line=c.line,
                    code="CMT-001",
                    message=f"Commented-out code: {c.text[:60]}",
                    fix="Delete it; version control remembers",
                )
                for c in comments
                if _looks_like_code(text=c.text)
            )
        if self.flag_verbose:
            found.extend(self._verbose_violations(comments=comments, relative_file=relative_file))
        if self.flag_em_dash or self.flag_emoji:
            for comment in comments:
                found.extend(
                    self._style_violations(text=comment.text, line=comment.line, relative_file=relative_file)
                )
            for line, text in _docstring_lines(tree=tree):
                found.extend(self._style_violations(text=text, line=line, relative_file=relative_file))
        if self.flag_restating:
            found.extend(self._restating_violations(comments=comments, tree=tree, relative_file=relative_file))
        return found

    def _restating_violations(
        self,
        *,
        comments: list[_Comment],
        tree: ast.Module,
        relative_file: str,
    ) -> list[Violation]:
        stmt_index = _build_stmt_index(tree=tree)
        ctx = _RestatingContext(
            stmt_index=stmt_index,
            stmt_lines=sorted(stmt_index),
            standalone_lines={c.line for c in comments if c.standalone},
        )
        found: list[Violation] = []
        for comment in comments:
            if comment.standalone and _in_comment_block(comment=comment, standalone_lines=ctx.standalone_lines):
                continue
            if not comment.standalone and not ALLOW_TRAILING:
                continue
            s = _adjacent_statement(comment=comment, ctx=ctx)
            if s is None or not _is_simple_statement(s=s):
                continue
            if _restates_v2(comment=comment, s=s):
                found.append(
                    _violation(
                        relative_file=relative_file,
                        line=comment.line,
                        code="CMT-005",
                        message=f"Comment restates the code: {comment.text[:50]}",
                        fix="Remove it, or explain the why rather than the what",
                    )
                )
        return found

    def run(self, *, src_root: str) -> CheckResult:
        violations: list[Violation] = []
        root = Path(src_root)
        for py_file in sorted(root.rglob("*.py")):
            if any(part in _SKIP_DIRS for part in py_file.parts):
                continue
            try:
                source = py_file.read_text(encoding="utf-8")
                tree = ast.parse(source)
            except (OSError, UnicodeDecodeError, SyntaxError):
                continue
            source_lines = source.splitlines()
            violations.extend(
                self._scan_file(
                    tree=tree,
                    comments=_collect_comments(source=source, source_lines=source_lines),
                    source_lines=source_lines,
                    relative_file=str(py_file.relative_to(root)),
                )
            )

        status = Status.FAIL if violations else Status.PASS
        return CheckResult(check=self.name, status=status, violations=violations)


register(CommentsCheck())
