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
    {"the", "a", "an", "to", "of", "and", "or", "for", "in", "on", "is", "be", "this", "that", "it"}
)
_WORD = re.compile(r"[A-Za-z]+")


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


def _next_code_line(*, source_lines: list[str], after: int) -> str | None:
    """The first non-blank, non-comment source line after 1-based line *after*."""
    for raw in source_lines[after:]:
        stripped = raw.strip()
        if stripped and not stripped.startswith("#"):
            return stripped
    return None


def _restates(*, comment: str, code_line: str) -> bool:
    """True if a short comment's words are all echoed by the next code line."""
    words = [w.lower() for w in _WORD.findall(comment) if w.lower() not in _STOPWORDS]
    if not words or len(words) > 4:
        return False
    identifiers = [token.lower() for token in _WORD.findall(code_line)]
    return all(any(word in ident or ident in word for ident in identifiers) for word in words)


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
            found.extend(self._restating_violations(comments=comments, source_lines=source_lines, relative_file=relative_file))
        return found

    def _restating_violations(
        self,
        *,
        comments: list[_Comment],
        source_lines: list[str],
        relative_file: str,
    ) -> list[Violation]:
        found: list[Violation] = []
        for comment in comments:
            if not comment.standalone:
                continue
            code_line = _next_code_line(source_lines=source_lines, after=comment.line)
            if code_line and _restates(comment=comment.text, code_line=code_line):
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
