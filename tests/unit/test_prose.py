"""Tests for the prose check (PROSE-001/002/003), the Markdown house-style scanner.

The prose check is opt-in and only scans configured documentation extensions
(default ``.md`` / ``.markdown``). It must skip fenced code blocks and inline
code spans so code samples are never flagged, and it must never touch ``.py``
sources (Python comments/docstrings are the comments check's job). A false
positive on correct prose is the cardinal sin for this check.

NOTE on the fixture idiom: ``ProseCheck`` is *off by default*; ``run`` short-
circuits to PASS when ``enabled`` is False. Every test therefore constructs the
check with ``enabled=True`` (directly or via ``configure``); otherwise the
assertions would pass vacuously.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from lanorme import Status
from lanorme.checks.prose import ProseCheck

# Unicode literals used by the fixtures (kept out of the prose to avoid
# accidentally triggering the very rules under test in this file's own text).
_EM_DASH = "—"  # em dash (PROSE-001)
_EN_DASH = "–"  # en dash (must NOT trip PROSE-001)
_ROCKET = "\U0001f680"  # rocket emoji (PROSE-003)
_PARTY = "\U0001f389"  # party emoji
_ARROW = "→"  # right arrow (must NOT trip PROSE-003)
_BULLET = "•"  # bullet (must NOT trip PROSE-003)
_CHECK = "✔"  # dingbat check mark (IS flagged as emoji)


@pytest.fixture
def check() -> ProseCheck:
    """An *enabled* prose check with default settings (md/markdown, all rules on)."""
    return ProseCheck(enabled=True)


def _write(*, root: Path, name: str, body: str) -> None:
    """Write a documentation/source file under *root*."""
    (root / name).write_text(body, encoding="utf-8")


# --------------------------------------------------------------------------- #
# Off-by-default contract
# --------------------------------------------------------------------------- #


def test_disabled_by_default_never_fires(tmp_path: Path):
    # Arrange: a default (disabled) check over a file full of violations.
    _write(root=tmp_path, name="doc.md", body=f"color {_EM_DASH} {_ROCKET}\n")

    # Act: run the check without enabling it.
    result = ProseCheck().run(src_root=str(tmp_path))

    # Assert: opt-in means silence until configured on.
    assert result.status == Status.PASS
    assert result.violations == []


# --------------------------------------------------------------------------- #
# PROSE-002 (US -> UK spelling): true positive, true negative, edges
# --------------------------------------------------------------------------- #


def test_prose002_flags_american_spelling(check: ProseCheck, tmp_path: Path):
    # Arrange: plain prose with three high-confidence US spellings.
    _write(root=tmp_path, name="doc.md", body="Use color and analyze the behavior.\n")

    # Act.
    result = check.run(src_root=str(tmp_path))

    # Assert: each US word is reported with its British fix.
    assert result.status == Status.FAIL
    spell = [v for v in result.violations if v.rule == "PROSE-002"]
    words = {v.message for v in spell}
    assert "American spelling 'color' found" in words
    assert "American spelling 'analyze' found" in words
    assert "American spelling 'behavior' found" in words
    assert any(v.fix == "Use British spelling 'colour'" for v in spell)


def test_prose002_silent_on_british_spelling(check: ProseCheck, tmp_path: Path):
    # Arrange: the British forms of the same words.
    _write(
        root=tmp_path,
        name="doc.md",
        body="The colour scheme is organised and we analyse behaviour.\n",
    )

    # Act.
    result = check.run(src_root=str(tmp_path))

    # Assert: correct prose stays silent.
    assert result.status == Status.PASS
    assert result.violations == []


def test_prose002_respects_word_boundaries(check: ProseCheck, tmp_path: Path):
    # Arrange: 'color' only as a substring of larger, correctly-spelled words.
    _write(root=tmp_path, name="doc.md", body="The word colorful and discolored appear.\n")

    # Act.
    result = check.run(src_root=str(tmp_path))

    # Assert: \b boundaries mean no false positive on embedded substrings.
    assert result.status == Status.PASS
    assert result.violations == []


def test_prose002_is_case_insensitive_but_fix_keeps_canonical_form(
    check: ProseCheck, tmp_path: Path
):
    # Arrange: a title-cased US spelling.
    _write(root=tmp_path, name="doc.md", body="Color is nice.\n")

    # Act.
    result = check.run(src_root=str(tmp_path))

    # Assert: 'Color' fires; the message echoes the source casing while the fix
    # uses the canonical lower-case British form.
    spell = [v for v in result.violations if v.rule == "PROSE-002"]
    assert len(spell) == 1
    assert spell[0].message == "American spelling 'Color' found"
    assert spell[0].fix == "Use British spelling 'colour'"


def test_prose002_omits_part_of_speech_ambiguous_pairs(check: ProseCheck, tmp_path: Path):
    # Arrange: license/practice/program are intentionally NOT in the map.
    _write(
        root=tmp_path,
        name="doc.md",
        body="The license and practice and program are fine.\n",
    )

    # Act.
    result = check.run(src_root=str(tmp_path))

    # Assert: ambiguous pairs do not fire.
    assert result.status == Status.PASS
    assert result.violations == []


# --------------------------------------------------------------------------- #
# PROSE-001 (em dash) and PROSE-003 (emoji)
# --------------------------------------------------------------------------- #


def test_prose001_flags_em_dash_only(check: ProseCheck, tmp_path: Path):
    # Arrange: an em dash and, separately, an en dash (the look-alike).
    _write(
        root=tmp_path,
        name="doc.md",
        body=f"A sentence {_EM_DASH} with em dash.\nRange 1{_EN_DASH}10 uses en dash.\n",
    )

    # Act.
    result = check.run(src_root=str(tmp_path))

    # Assert: only the em-dash line trips PROSE-001; the en dash is left alone.
    em = [v for v in result.violations if v.rule == "PROSE-001"]
    assert len(em) == 1
    assert em[0].line == 1


def test_prose003_flags_emoji_but_not_typographic_symbols(check: ProseCheck, tmp_path: Path):
    # Arrange: one true emoji, plus arrow/bullet symbols that belong in prose.
    _write(root=tmp_path, name="emoji.md", body=f"Great work {_ROCKET} here.\n")
    _write(root=tmp_path, name="typo.md", body=f"Flow {_ARROW} and bullet {_BULLET} point.\n")

    # Act.
    result = check.run(src_root=str(tmp_path))

    # Assert: the emoji fires; arrows and bullets never do.
    emoji = [v for v in result.violations if v.rule == "PROSE-003"]
    assert len(emoji) == 1
    assert emoji[0].file == "emoji.md"
    assert _ROCKET in emoji[0].message


def test_prose003_reports_one_emoji_per_line(check: ProseCheck, tmp_path: Path):
    # Arrange: two emoji on a single line (scanner uses search, first match wins).
    _write(root=tmp_path, name="doc.md", body=f"Two {_ROCKET} and {_PARTY} emoji.\n")

    # Act.
    result = check.run(src_root=str(tmp_path))

    # Assert: exactly one PROSE-003 per line, reporting the first emoji.
    emoji = [v for v in result.violations if v.rule == "PROSE-003"]
    assert len(emoji) == 1
    assert _ROCKET in emoji[0].message


def test_prose003_flags_dingbat_checkmark(check: ProseCheck, tmp_path: Path):
    # Arrange: a dingbat checkmark (U+2714) lies in a declared emoji range.
    _write(root=tmp_path, name="doc.md", body=f"Done {_CHECK} now.\n")

    # Act.
    result = check.run(src_root=str(tmp_path))

    # Assert: it is flagged as an emoji.
    emoji = [v for v in result.violations if v.rule == "PROSE-003"]
    assert len(emoji) == 1
    assert _CHECK in emoji[0].message


def test_all_three_rules_on_one_line(check: ProseCheck, tmp_path: Path):
    # Arrange: a single line carrying a spelling, an em dash and an emoji.
    _write(root=tmp_path, name="doc.md", body=f"color {_EM_DASH} {_ROCKET}\n")

    # Act.
    result = check.run(src_root=str(tmp_path))

    # Assert: all three codes are present.
    codes = {v.rule for v in result.violations}
    assert codes == {"PROSE-001", "PROSE-002", "PROSE-003"}


# --------------------------------------------------------------------------- #
# Skipping: fenced code, inline code, non-doc files
# --------------------------------------------------------------------------- #


def test_fenced_code_block_is_skipped(check: ProseCheck, tmp_path: Path):
    # Arrange: US spelling inside a ``` fence; British prose outside it.
    body = "Intro colour ok.\n```python\ncolor = optimize(behavior)\n```\nOutro colour ok.\n"
    _write(root=tmp_path, name="doc.md", body=body)

    # Act.
    result = check.run(src_root=str(tmp_path))

    # Assert: nothing inside the fence fires.
    assert result.status == Status.PASS
    assert result.violations == []


def test_tilde_fence_is_skipped_but_outside_prose_still_scanned(
    check: ProseCheck, tmp_path: Path
):
    # Arrange: US spelling inside a ~~~ fence, plus a US spelling after it.
    body = "Intro colour ok.\n~~~\ncolor analyze\n~~~\nOutro behavior here.\n"
    _write(root=tmp_path, name="doc.md", body=body)

    # Act.
    result = check.run(src_root=str(tmp_path))

    # Assert: only the post-fence 'behavior' fires; fence content is exempt.
    spell = [v for v in result.violations if v.rule == "PROSE-002"]
    assert len(spell) == 1
    assert spell[0].line == 5
    assert "behavior" in spell[0].message


def test_strikethrough_two_tildes_is_not_a_fence(check: ProseCheck, tmp_path: Path):
    # Arrange: GFM strikethrough uses TWO tildes; only THREE open a fence.
    _write(root=tmp_path, name="doc.md", body="This ~~old~~ text has behavior in it.\n")

    # Act.
    result = check.run(src_root=str(tmp_path))

    # Assert: the line is still scanned; 'behavior' fires.
    spell = [v for v in result.violations if v.rule == "PROSE-002"]
    assert len(spell) == 1
    assert "behavior" in spell[0].message


def test_single_backtick_inline_code_is_skipped(check: ProseCheck, tmp_path: Path):
    # Arrange: the docstring's exact promise -- single-backtick code spans with
    # US spellings must not be flagged.
    _write(
        root=tmp_path,
        name="doc.md",
        body="A `color` span and an `optimize` span are skipped.\n",
    )

    # Act.
    result = check.run(src_root=str(tmp_path))

    # Assert: inline code is exempt.
    assert result.status == Status.PASS
    assert result.violations == []


def test_python_files_are_not_scanned_by_prose(check: ProseCheck, tmp_path: Path):
    # Arrange: a .py file whose comment and string literal contain US spellings
    # and an em dash. The prose check owns Markdown only.
    _write(
        root=tmp_path,
        name="mod.py",
        body=f'# color analyze behavior {_EM_DASH}\nx = "color optimize"\n',
    )

    # Act.
    result = check.run(src_root=str(tmp_path))

    # Assert: .py is outside the configured extensions -> silence.
    assert result.status == Status.PASS
    assert result.violations == []


# --------------------------------------------------------------------------- #
# Configuration: toggles and custom spellings
# --------------------------------------------------------------------------- #


def test_toggles_disable_em_dash_and_emoji(tmp_path: Path):
    # Arrange: enable prose but turn off em-dash and emoji rules.
    check = ProseCheck()
    check.configure(settings={"enabled": True, "em_dash": False, "emoji": False})
    _write(root=tmp_path, name="doc.md", body=f"color {_EM_DASH} {_ROCKET}\n")

    # Act.
    result = check.run(src_root=str(tmp_path))

    # Assert: only the spelling rule remains active.
    codes = {v.rule for v in result.violations}
    assert codes == {"PROSE-002"}


def test_custom_spellings_extend_the_map(tmp_path: Path):
    # Arrange: register a custom US->UK pair on top of the defaults.
    check = ProseCheck()
    check.configure(settings={"enabled": True, "spellings": {"gotten": "got"}})
    _write(root=tmp_path, name="doc.md", body="I have gotten color here.\n")

    # Act.
    result = check.run(src_root=str(tmp_path))

    # Assert: both the custom word and a default word fire.
    messages = {v.message for v in result.violations if v.rule == "PROSE-002"}
    assert "American spelling 'gotten' found" in messages
    assert "American spelling 'color' found" in messages


# --------------------------------------------------------------------------- #
# CONFIRMED BUG (pinned, not asserted as correct): double-backtick inline code
# --------------------------------------------------------------------------- #


def test_double_backtick_inline_code_should_be_skipped(check: ProseCheck, tmp_path: Path):
    # Arrange: US spellings and an em dash inside DOUBLE-backtick inline spans,
    # exactly as the docstring promises will not be flagged.
    _write(
        root=tmp_path,
        name="doc.md",
        body=f"Use ``color`` and ``optimize`` and ``a {_EM_DASH} b`` inline.\n",
    )

    # Act.
    result = check.run(src_root=str(tmp_path))

    # Assert (desired behaviour): inline code is exempt, so nothing fires.
    assert result.status == Status.PASS
    assert result.violations == []


# --------------------------------------------------------------------------- #
# PROSE-004 (em-dash density advisory): opt-in, floor, the AND of both axes
# --------------------------------------------------------------------------- #


def _density_check() -> ProseCheck:
    """A prose check with PROSE-004 enabled and the PROSE-001 ban switched off.

    This models the task's ban -> density switch: with ``em_dash`` off, PROSE-001
    never fires, so the only finding on a dense doc is the PROSE-004 warning.
    """
    check = ProseCheck()
    check.configure(settings={"enabled": True, "em_dash": False, "em_dash_density": True})
    return check


def _sentence(*, words: int, em_dashes: int) -> str:
    """Build one sentence with *words* words and *em_dashes* em dashes, full-stopped."""
    tokens = ["word"] * words
    for i in range(em_dashes):
        # Surround the em dash with spaces so it never fuses two word tokens.
        tokens[2 * i + 1] = f"{_EM_DASH} word"
    return " ".join(tokens) + "."


def test_prose004_fires_on_llm_style_dense_doc(tmp_path: Path):
    # Arrange: 32 sentences, each 20 words with 2 em dashes. That is 640 words,
    # 64 em dashes (100 per 1000) and 32/32 sentences carrying one -> both axes
    # clear their thresholds, so the advisory must fire.
    body = " ".join(_sentence(words=20, em_dashes=2) for _ in range(32)) + "\n"
    _write(root=tmp_path, name="llm.md", body=body)

    # Act.
    result = _density_check().run(src_root=str(tmp_path))

    # Assert: one PROSE-004 warning (not a violation), anchored at line 1.
    assert result.violations == []
    warnings = [w for w in result.warnings if w.code == "PROSE-004"]
    assert len(warnings) == 1
    assert warnings[0].line == 1
    assert result.status == Status.WARN


def test_prose004_silent_on_natural_long_doc(tmp_path: Path):
    # Arrange: a long doc with only a handful of em dashes in a low fraction of
    # sentences. Words and sentences clear the floor, but neither fire axis does.
    plain = [_sentence(words=20, em_dashes=0) for _ in range(36)]
    dashed = [_sentence(words=20, em_dashes=1) for _ in range(4)]
    body = " ".join(plain + dashed) + "\n"
    _write(root=tmp_path, name="natural.md", body=body)

    # Act.
    result = _density_check().run(src_root=str(tmp_path))

    # Assert: natural prose stays silent.
    assert [w for w in result.warnings if w.code == "PROSE-004"] == []


def test_prose004_does_not_fire_when_only_one_axis_is_high(tmp_path: Path):
    # Arrange: the AND discriminator. Cram many em dashes into 2 of 40 sentences
    # so the per-1000 rate clears its threshold (about 31 per 1000) while the
    # sentence fraction is only 5%. An OR bug would fire here; the spec's AND
    # must not. (The doc still clears the eligibility floor, so this exercises
    # the fire logic rather than the floor.)
    heavy = [_sentence(words=40, em_dashes=13) for _ in range(2)]
    plain = [_sentence(words=20, em_dashes=0) for _ in range(38)]
    body = " ".join(heavy + plain) + "\n"
    _write(root=tmp_path, name="skewed.md", body=body)

    # Act.
    result = _density_check().run(src_root=str(tmp_path))

    # Assert: high rate but low fraction -> no fire (AND, not OR).
    assert [w for w in result.warnings if w.code == "PROSE-004"] == []


def test_prose004_silent_below_eligibility_floor(tmp_path: Path):
    # Arrange: a short doc with just 2 em dashes, below the em>=4 floor (and far
    # below the word/sentence floors). Density must never fire on so little text.
    _write(
        root=tmp_path,
        name="short.md",
        body=f"A short note {_EM_DASH} with two dashes {_EM_DASH} only.\n",
    )

    # Act.
    result = _density_check().run(src_root=str(tmp_path))

    # Assert: the floor keeps it silent.
    assert [w for w in result.warnings if w.code == "PROSE-004"] == []


def test_prose004_silent_by_default_when_not_enabled(tmp_path: Path):
    # Arrange: the same dense doc that fires above, but density NOT enabled (only
    # base prose). PROSE-004 is opt-in, so it must produce no warning.
    body = " ".join(_sentence(words=20, em_dashes=2) for _ in range(32)) + "\n"
    _write(root=tmp_path, name="llm.md", body=body)
    check = ProseCheck()
    check.configure(settings={"enabled": True, "em_dash": False})

    # Act.
    result = check.run(src_root=str(tmp_path))

    # Assert: opt-in means no density warning until em_dash_density is set.
    assert [w for w in result.warnings if w.code == "PROSE-004"] == []


def test_prose004_ignores_em_dashes_inside_fenced_code(tmp_path: Path):
    # Arrange: a dense block of em dashes lives entirely inside a fence; the prose
    # around it is clean. Density measures prose only, so the fence cannot trip it.
    dense = " ".join(_sentence(words=20, em_dashes=2) for _ in range(32))
    body = f"Intro prose is clean here.\n```\n{dense}\n```\nOutro prose is clean too.\n"
    _write(root=tmp_path, name="fenced.md", body=body)

    # Act.
    result = _density_check().run(src_root=str(tmp_path))

    # Assert: em dashes inside the fence never count.
    assert [w for w in result.warnings if w.code == "PROSE-004"] == []
