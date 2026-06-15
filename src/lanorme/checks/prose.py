"""PROSE-001 / PROSE-002 / PROSE-003 / PROSE-004: Prose style for Markdown and docs.

An opt-in check for documentation files (Markdown by default). It enforces a
house style for prose:

    PROSE-001  No em dashes. Rewrite with commas, parentheses, or a full stop.
    PROSE-002  British spelling, flag American spellings and suggest the British form.
    PROSE-003  No emoji.
    PROSE-004  Em-dash density above natural English (advisory warning, opt-in).

Fenced code blocks (``` … ```) and inline ``code`` spans are skipped, so code
samples that contain ``color`` or ``optimize`` are not flagged. PROSE-004 reuses
that same stripping and measures density over the remaining prose alone.

Off by default, it only runs when enabled, so it never imposes a house style on
a project that has not opted in::

    [tool.lanorme.prose]
    enabled = true
    extensions = [".md", ".rst"]   # default: [".md", ".markdown"]
    em_dash = true                 # default true (PROSE-001 outright ban)
    emoji = true                   # default true
    em_dash_density = true         # default false (PROSE-004 advisory)

    [tool.lanorme.prose.spellings]
    customize = "customise"        # extend / override the built-in US->UK map

    [tool.lanorme.prose.density]
    min_em = 4                     # eligibility floor: minimum em dashes
    min_words = 400                # eligibility floor: minimum words
    min_sentences = 30             # eligibility floor: minimum sentences
    em_per_1000 = 30.0             # fire threshold: em dashes per 1000 words
    em_sentence_fraction = 0.50    # fire threshold: fraction of sentences with an em dash

Setting ``em_dash = false`` while ``em_dash_density = true`` switches a region
from the PROSE-001 ban to the PROSE-004 density advisory.

Run:
    lanorme check . --check=prose
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from lanorme import CheckResult, Status, Violation, register
from lanorme.discovery import iter_files

_EM_DASH = "—"

# Value types a ``[tool.lanorme.prose]`` table can carry: scalar toggles, the
# extensions list, and the spellings / density sub-tables. Spelled as a union of
# concrete leaves (no bare ``object``) so it reads as the real config shape.
ProseSettings = dict[
    str, bool | int | float | list[str] | dict[str, str] | dict[str, float]
]

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

# A code span is a run of backticks, then content, then a matching run of the
# same length (CommonMark). The backreference is what makes double-backtick
# spans like ``color`` strip correctly; a single-backtick pattern would only
# blank the delimiter pairs and leave the content exposed to the scanner.
_INLINE_CODE = re.compile(r"(`+).*?\1")

# Word and sentence segmentation for PROSE-004 density. Sentences split on a
# terminal ``.!?`` followed by whitespace; segments are kept only when they hold
# non-whitespace, so trailing or doubled breaks cannot inflate the count.
_WORD = re.compile(r"\b\w+\b")
_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")

# Corpus-calibrated PROSE-004 thresholds. The eligibility floor keeps the rule
# silent on anything too short to measure; the two fire thresholds are ANDed so
# a single high axis cannot trip it.
_DENSITY_DEFAULTS: dict[str, float] = {
    "min_em": 4,
    "min_words": 400,
    "min_sentences": 30,
    "em_per_1000": 30.0,
    "em_sentence_fraction": 0.50,
}

# Vendored / generated directories never scanned for prose.
_SKIP_PARTS = frozenset(
    {".git", ".venv", "venv", "node_modules", "__pycache__", "dist", "build"}
)


def _strip_inline_code(line: str) -> str:
    """Blank out inline `code` spans, preserving length for column fidelity."""
    return _INLINE_CODE.sub(lambda m: " " * len(m.group(0)), line)


def _status_for(*, violations: list[Violation], warnings: list[Violation]) -> Status:
    """Map findings to a status: any hard violation fails, an advisory warns."""
    if violations:
        return Status.FAIL
    if warnings:
        return Status.WARN
    return Status.PASS


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
    flag_em_dash_density: bool = False
    spellings: dict[str, str] = field(default_factory=lambda: dict(_DEFAULT_SPELLINGS))
    density: dict[str, float] = field(default_factory=lambda: dict(_DENSITY_DEFAULTS))
    rules: list[str] = field(
        default_factory=lambda: [
            "PROSE-001: No em dashes in prose",
            "PROSE-002: Use British spelling (no American spellings)",
            "PROSE-003: No emoji in prose",
            "PROSE-004: Em-dash density above natural English",
        ]
    )

    def configure(self, *, settings: ProseSettings) -> None:
        """Apply ``[tool.lanorme.prose]`` configuration."""
        if "enabled" in settings:
            self.enabled = bool(settings["enabled"])
        if "em_dash" in settings:
            self.flag_em_dash = bool(settings["em_dash"])
        if "emoji" in settings:
            self.flag_emoji = bool(settings["emoji"])
        if "em_dash_density" in settings:
            self.flag_em_dash_density = bool(settings["em_dash_density"])
        extensions = settings.get("extensions")
        if isinstance(extensions, list):
            self.extensions = tuple(ext.lower() for ext in extensions)
        spellings = settings.get("spellings")
        if isinstance(spellings, dict):
            self.spellings = {**self.spellings, **spellings}
        density = settings.get("density")
        if isinstance(density, dict):
            self._apply_density(table=density)

    def _apply_density(self, *, table: dict[str, float]) -> None:
        """Merge a ``[tool.lanorme.prose.density]`` table over the defaults."""
        for key in _DENSITY_DEFAULTS:
            if key in table:
                self.density[key] = table[key]

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

    def _prose_lines(self, *, text: str) -> list[tuple[int, str]]:
        """Yield ``(lineno, prose_line)`` with fenced and inline code removed.

        The single source of truth for what counts as prose: fenced code blocks
        (``` or ~~~) are dropped and inline code spans are blanked. Both the
        line scanners (PROSE-001/002/003) and the density measure (PROSE-004)
        consume this, so they always agree on the prose surface.
        """
        lines: list[tuple[int, str]] = []
        in_fence = False
        for lineno, raw in enumerate(text.splitlines(), start=1):
            stripped = raw.lstrip()
            if stripped.startswith("```") or stripped.startswith("~~~"):
                in_fence = not in_fence
                continue
            if in_fence:
                continue
            lines.append((lineno, _strip_inline_code(raw)))
        return lines

    def _scan_text(
        self,
        *,
        text: str,
        relative_file: str,
        spell_re: re.Pattern[str] | None,
    ) -> list[Violation]:
        violations: list[Violation] = []
        for lineno, line in self._prose_lines(text=text):
            violations.extend(
                self._scan_line(
                    line=line,
                    lineno=lineno,
                    relative_file=relative_file,
                    spell_re=spell_re,
                )
            )
        return violations

    def _density_warning(self, *, text: str, relative_file: str) -> Violation | None:
        """PROSE-004: one advisory warning per file when em-dash density is high.

        Measured over prose only (fenced and inline code stripped). Stays silent
        below the eligibility floor, then fires only when BOTH the per-1000-word
        rate and the fraction of sentences carrying an em dash clear their
        thresholds. The AND is deliberate.
        """
        prose = "\n".join(line for _, line in self._prose_lines(text=text))
        em = prose.count(_EM_DASH)
        words = len(_WORD.findall(prose))
        segments = [seg for seg in _SENTENCE_SPLIT.split(prose) if seg.strip()]
        sentences = len(segments)
        if em < self.density["min_em"] or words < self.density["min_words"]:
            return None
        if sentences < self.density["min_sentences"]:
            return None

        per_1000 = em / words * 1000
        with_em = sum(1 for seg in segments if _EM_DASH in seg)
        fraction = with_em / sentences
        if per_1000 < self.density["em_per_1000"]:
            return None
        if fraction < self.density["em_sentence_fraction"]:
            return None

        return Violation(
            file=relative_file,
            line=1,
            rule="PROSE-004: Em-dash density above natural English",
            message=(
                f"Em-dash density {per_1000:.1f} per 1000 words across "
                f"{int(fraction * 100)}% of sentences reads as machine-generated"
            ),
            fix="Vary the punctuation: replace em dashes with commas, parentheses, or full stops",
        )

    def _scan_file(
        self,
        *,
        path: Path,
        root: Path,
        spell_re: re.Pattern[str] | None,
    ) -> tuple[list[Violation], list[Violation]]:
        """Scan one doc file, returning its ``(violations, warnings)``."""
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            return [], []
        relative_file = str(path.relative_to(root))
        violations = self._scan_text(
            text=text,
            relative_file=relative_file,
            spell_re=spell_re,
        )
        warnings: list[Violation] = []
        if self.flag_em_dash_density:
            warning = self._density_warning(text=text, relative_file=relative_file)
            if warning is not None:
                warnings.append(warning)
        return violations, warnings

    def _is_doc(self, *, path: Path) -> bool:
        """True if *path* is a documentation file this check should scan."""
        if path.suffix.lower() not in self.extensions or not path.is_file():
            return False
        return not any(part in _SKIP_PARTS for part in path.parts)

    def run(self, *, src_root: str) -> CheckResult:
        if not self.enabled:
            return CheckResult(check=self.name, status=Status.PASS, violations=[])

        violations: list[Violation] = []
        warnings: list[Violation] = []
        spell_re = _compile_spellings(self.spellings)
        root = Path(src_root)

        for path in iter_files(root):
            if not self._is_doc(path=path):
                continue
            file_violations, file_warnings = self._scan_file(
                path=path, root=root, spell_re=spell_re
            )
            violations.extend(file_violations)
            warnings.extend(file_warnings)

        return CheckResult(
            check=self.name,
            status=_status_for(violations=violations, warnings=warnings),
            violations=violations,
            warnings=warnings,
        )


register(ProseCheck())
