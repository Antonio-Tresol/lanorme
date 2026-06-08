"""CMT-001 and CMT-002 (and PROSE-001 / PROSE-003 when enabled).

Selectable rules for the quality of ``#`` comments (and, for the style rules,
docstrings):

    CMT-001    No commented-out code.
    CMT-002    No verbose comments (block too long, or line too long).
    PROSE-001  No em dashes in comments or docstrings (shares the PROSE family
               with the markdown check; opt-in via ``em_dash = true``).
    PROSE-003  No emoji in comments or docstrings (shares the PROSE family;
               opt-in via ``emoji = true``).

CMT-001 and CMT-002 are hygiene and run by default. The PROSE rules stay off
until enabled::

    [tool.lanorme.comments]
    em_dash = true       # emit PROSE-001 on comments/docstrings
    emoji = true         # emit PROSE-003 on comments/docstrings
    max_block_lines = 6
    max_comment_chars = 120

CMT-005 (restating-comment detector) lives in its own ``restating`` check;
opt in via ``[tool.lanorme.restating] enabled = true``.

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
from lanorme.discovery import iter_py_files

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
    ast.AsyncFor,
    ast.While,
    ast.If,
    ast.Try,
    ast.Match,
    ast.With,
    ast.AsyncWith,
    ast.Delete,
    ast.Raise,
    ast.Assert,
    ast.Return,
)

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


def _is_code_statement(node: ast.stmt) -> bool:
    """True if *node* is a statement type we treat as commented-out code."""
    # 'label: type' without a value reads as documentation, not an assignment.
    if isinstance(node, ast.AnnAssign) and node.value is None:
        return False
    # 'foo(...)' with a literal ellipsis is illustrative, not dead code.
    if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
        return not _has_ellipsis_arg(call=node.value)
    return isinstance(node, _CODE_NODES)


# Block-header keywords whose comments don't parse standalone (they require a
# body). We try wrapping with ``pass`` to make them syntactically complete.
_BLOCK_HEADER_KEYWORDS = (
    "if ", "elif ", "else:", "for ", "while ", "try:", "except", "finally:",
    "with ", "match ", "case ", "def ", "async def ", "class ",
)
# Bare keyword statements that need an enclosing function to parse.
_SCOPE_BOUND_KEYWORDS = ("return", "yield", "raise", "await ")


def _parsing_candidates(text: str) -> list[str]:
    """Variants of *text* to try, covering Python shapes that don't parse standalone."""
    stripped = text.strip()
    candidates: list[str] = [text]
    if stripped.endswith(":") and stripped.startswith(_BLOCK_HEADER_KEYWORDS):
        candidates.append(text + "\n    pass")
    # ``try:`` alone is invalid; it needs an ``except`` or ``finally`` clause.
    if stripped == "try:" or (stripped.startswith("try ") and stripped.endswith(":")):
        candidates.append(text + "\n    pass\nexcept Exception:\n    pass")
    # ``elif`` / ``else`` and ``except`` / ``finally`` need a preceding parent.
    if stripped.startswith(("elif ", "else:")):
        candidates.append(f"if True:\n    pass\n{text}\n    pass")
    if stripped.startswith(("except", "finally:")):
        candidates.append(f"try:\n    pass\n{text}\n    pass")
    # Bare ``return`` / ``yield`` / ``raise`` / ``await`` need an enclosing def.
    first_word = stripped.split(" ", 1)[0] if stripped else ""
    if first_word in {"return", "yield", "raise"} or any(
        stripped.startswith(k) for k in _SCOPE_BOUND_KEYWORDS
    ):
        candidates.append(f"def _():\n    {text}")
    # Decorator lines (``@foo`` / ``@app.route(...)``) need a target def.
    if stripped.startswith("@"):
        candidates.append(f"{text}\ndef _():\n    pass")
    return candidates


def _comment_parses_as_code(text: str) -> bool:
    """Return True if the comment text resolves to a code statement."""
    for candidate in _parsing_candidates(text):
        try:
            tree = ast.parse(candidate)
        except (SyntaxError, ValueError, RecursionError):
            # A deeply nested but parseable expression in a single comment can
            # overflow the parser. Treat it as prose, not commented-out code.
            continue
        for node in tree.body:
            if _is_code_statement(node):
                return True
            # Unwrap the synthetic ``def _():`` used for scope-bound text.
            if isinstance(node, ast.FunctionDef) and node.name == "_":
                if any(_is_code_statement(child) for child in node.body):
                    return True
    return False


def _looks_like_code(*, text: str) -> bool:
    """True if a comment body parses as a code statement rather than prose."""
    if not text or text.startswith(_PRAGMA_PREFIXES) or text.endswith((".", "?", "!")):
        return False
    return _comment_parses_as_code(text)


# PEP 723 inline script metadata: a ``# /// <type>`` ... ``# ///`` block whose
# inner lines are ``#`` or ``# <content>``. The body is TOML, so a line like
# ``# dependencies = ["rich"]`` parses as an assignment and would otherwise be
# flagged as commented-out code. These lines are tooling metadata, not dead code.
# This is the reference grammar from PEP 723; without the closing ``# ///`` fence
# nothing matches, so a stray opener stays lintable.
_PEP723_BLOCK = re.compile(r"(?m)^# /// [a-zA-Z0-9-]+$\s(?:^#(?: .*)?$\s)*?^# ///$")


def _pep723_metadata_lines(source_lines: list[str]) -> frozenset[int]:
    """Return the 1-based line numbers inside any PEP 723 inline-metadata block."""
    source = "\n".join(source_lines)
    flagged: set[int] = set()
    for match in _PEP723_BLOCK.finditer(source):
        first = source.count("\n", 0, match.start()) + 1
        flagged.update(range(first, first + match.group().count("\n") + 1))
    return frozenset(flagged)


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
    max_block_lines: int = 6
    max_comment_chars: int = 120
    rules: list[str] = field(
        default_factory=lambda: [
            "CMT-001: No commented-out code",
            "CMT-002: No verbose comments (block or line too long)",
            "PROSE-001: No em dashes in comments or docstrings (opt-in)",
            "PROSE-003: No emoji in comments or docstrings (opt-in)",
        ]
    )

    def configure(self, *, settings: dict[str, bool | int]) -> None:
        """Apply ``[tool.lanorme.comments]`` configuration."""
        for key in ("flag_commented_code", "flag_verbose"):
            short = key.removeprefix("flag_")
            if short in settings:
                setattr(self, key, bool(settings[short]))
        for short in ("em_dash", "emoji"):
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
                    code="PROSE-001",
                    message="Em dash in comment/docstring",
                    fix="Rewrite with a comma, parentheses, or a full stop",
                )
            )
        if self.flag_emoji and _EMOJI.search(text):
            found.append(
                _violation(
                    relative_file=relative_file,
                    line=line,
                    code="PROSE-003",
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
            metadata_lines = _pep723_metadata_lines(source_lines)
            found.extend(
                _violation(
                    relative_file=relative_file,
                    line=c.line,
                    code="CMT-001",
                    message=f"Commented-out code: {c.text[:60]}",
                    fix="Delete it; version control remembers",
                )
                for c in comments
                if c.line not in metadata_lines and _looks_like_code(text=c.text)
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
        return found

    def run(self, *, src_root: str) -> CheckResult:
        violations: list[Violation] = []
        root = Path(src_root)
        for py_file in iter_py_files(root):
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
