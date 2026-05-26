"""PROSE-001 / PROSE-002 / PROSE-003: Prose style for Markdown and docs.

An opt-in check for documentation files (Markdown by default). It enforces a
house style for prose:

    PROSE-001  No em dashes (-). Rewrite with commas, parentheses, or a full stop.
    PROSE-002  British spelling, flag American spellings and suggest the British form.
    PROSE-003  No emoji.

Fenced code blocks (``` … ```) and inline ``code`` spans are skipped, so code
samples that contain ``color`` or ``optimize`` are not flagged.

Off by default, it only runs when enabled, so it never imposes a house style on
a project that has not opted in::

    [tool.lanorme.prose]
    enabled = true
    extensions = [".md", ".rst"]   # default: [".md", ".markdown"]
    em_dash = true                 # default true
    emoji = true                   # default true

    [tool.lanorme.prose.spellings]
    customize = "customise"        # extend / override the built-in US→UK map

Run:
    lanorme check . --check=prose
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from lanorme import CheckResult, Status, Violation, register

_EM_DASH = "—"

# Common emoji code-point ranges. Deliberately excludes plain arrows (←→) and
# other typographic symbols that appear legitimately in prose and diagrams.
_EMOJI = re.compile(
    "["
    "\U0001f300-\U0001faff"  # symbols, pictographs, emoticons, transport, supplemental
    "\U00002600-\U000026ff"  # miscellaneous symbols
    "\U00002700-\U000027bf"  # dingbats
    "\U0001f1e6-\U0001f1ff"  # regional indicator (flags)
    "\U00002b00-\U00002bff"  # stars and misc symbols
    "\U0000fe0f"  # emoji variation selector
    "\U0000200d"  # zero-width joiner
    "]"
)

# High-confidence American → British spellings. Part-of-speech-ambiguous pairs
# (license/licence, practice/practise, program) are intentionally omitted.
_DEFAULT_SPELLINGS: dict[str, str] = {
    "color": "colour",
    "colors": "colours",
    "colored": "coloured",
    "coloring": "colouring",
    "behavior": "behaviour",
    "behaviors": "behaviours",
    "flavor": "flavour",
    "flavors": "flavours",
    "favor": "favour",
    "favorite": "favourite",
    "honor": "honour",
    "labor": "labour",
    "neighbor": "neighbour",
    "organize": "organise",
    "organized": "organised",
    "organizing": "organising",
    "organization": "organisation",
    "recognize": "recognise",
    "recognized": "recognised",
    "analyze": "analyse",
    "analyzed": "analysed",
    "analyzing": "analysing",
    "initialize": "initialise",
    "customize": "customise",
    "optimize": "optimise",
    "normalize": "normalise",
    "synchronize": "synchronise",
    "center": "centre",
    "centered": "centred",
    "theater": "theatre",
    "meter": "metre",
    "liter": "litre",
    "defense": "defence",
    "offense": "offence",
    "gray": "grey",
    "traveler": "traveller",
    "traveling": "travelling",
    "canceled": "cancelled",
    "canceling": "cancelling",
    "modeling": "modelling",
    "fulfill": "fulfil",
    "catalog": "catalogue",
    "dialog": "dialogue",
}

_INLINE_CODE = re.compile(r"`[^`]*`")

# Vendored / generated directories never scanned for prose.
_SKIP_PARTS = frozenset(
    {".git", ".venv", "venv", "node_modules", "__pycache__", "dist", "build"}
)


def _strip_inline_code(line: str) -> str:
    """Blank out inline `code` spans, preserving length for column fidelity."""
    return _INLINE_CODE.sub(lambda m: " " * len(m.group(0)), line)


def _compile_spellings(spellings: dict[str, str]) -> re.Pattern[str] | None:
    if not spellings:
        return None
    alternation = "|".join(re.escape(word) for word in sorted(spellings, key=len, reverse=True))
    return re.compile(rf"\b({alternation})\b", re.IGNORECASE)


@dataclass
class ProseCheck:
    """Opt-in prose style for docs: em dashes, US spelling, emoji."""

    name: str = "prose"
    description: str = "Prose style for Markdown/docs (em dashes, US spelling, emoji)"
    enabled: bool = False
    extensions: tuple[str, ...] = (".md", ".markdown")
    flag_em_dash: bool = True
    flag_emoji: bool = True
    spellings: dict[str, str] = field(default_factory=lambda: dict(_DEFAULT_SPELLINGS))
    rules: list[str] = field(
        default_factory=lambda: [
            "PROSE-001: No em dashes in prose",
            "PROSE-002: Use British spelling (no American spellings)",
            "PROSE-003: No emoji in prose",
        ]
    )

    def configure(self, *, settings: dict[str, bool | list[str] | dict[str, str]]) -> None:
        """Apply ``[tool.lanorme.prose]`` configuration."""
        if "enabled" in settings:
            self.enabled = bool(settings["enabled"])
        if "em_dash" in settings:
            self.flag_em_dash = bool(settings["em_dash"])
        if "emoji" in settings:
            self.flag_emoji = bool(settings["emoji"])
        extensions = settings.get("extensions")
        if isinstance(extensions, list):
            self.extensions = tuple(ext.lower() for ext in extensions)
        spellings = settings.get("spellings")
        if isinstance(spellings, dict):
            self.spellings = {**self.spellings, **spellings}

    def _scan_line(
        self,
        *,
        line: str,
        lineno: int,
        relative_file: str,
        spell_re: re.Pattern[str] | None,
    ) -> list[Violation]:
        found: list[Violation] = []
        if self.flag_em_dash and _EM_DASH in line:
            found.append(
                Violation(
                    file=relative_file,
                    line=lineno,
                    rule="PROSE-001",
                    message="Em dash (—) found in prose",
                    fix="Rewrite with a comma, parentheses, or a full stop",
                )
            )
        if self.flag_emoji:
            match = _EMOJI.search(line)
            if match is not None:
                found.append(
                    Violation(
                        file=relative_file,
                        line=lineno,
                        rule="PROSE-003",
                        message=f"Emoji {match.group(0)!r} found in prose",
                        fix="Remove the emoji",
                    )
                )
        if spell_re is not None:
            for match in spell_re.finditer(line):
                word = match.group(0)
                found.append(
                    Violation(
                        file=relative_file,
                        line=lineno,
                        rule="PROSE-002",
                        message=f"American spelling '{word}' found",
                        fix=f"Use British spelling '{self.spellings[word.lower()]}'",
                    )
                )
        return found

    def _scan_text(
        self,
        *,
        text: str,
        relative_file: str,
        spell_re: re.Pattern[str] | None,
    ) -> list[Violation]:
        violations: list[Violation] = []
        in_fence = False
        for lineno, raw in enumerate(text.splitlines(), start=1):
            stripped = raw.lstrip()
            if stripped.startswith("```") or stripped.startswith("~~~"):
                in_fence = not in_fence
                continue
            if in_fence:
                continue
            violations.extend(
                self._scan_line(
                    line=_strip_inline_code(raw),
                    lineno=lineno,
                    relative_file=relative_file,
                    spell_re=spell_re,
                )
            )
        return violations

    def run(self, *, src_root: str) -> CheckResult:
        if not self.enabled:
            return CheckResult(check=self.name, status=Status.PASS, violations=[])

        violations: list[Violation] = []
        spell_re = _compile_spellings(self.spellings)
        root = Path(src_root)

        for path in sorted(root.rglob("*")):
            if path.suffix.lower() not in self.extensions or not path.is_file():
                continue
            if any(part in _SKIP_PARTS for part in path.parts):
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            violations.extend(
                self._scan_text(
                    text=text,
                    relative_file=str(path.relative_to(root)),
                    spell_re=spell_re,
                )
            )

        status = Status.FAIL if violations else Status.PASS
        return CheckResult(check=self.name, status=status, violations=violations)


register(ProseCheck())
