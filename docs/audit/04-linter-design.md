# LaNorme — Linter-Design Audit

Reviewer lens: tooling designer (ruff / pylint / mypy shipping perspective).
Source material: `README.md`, top docstring of each `src/lanorme/checks/*.py`,
and the `lanorme rules` output. Implementation bodies were not read.

## 1. Rule-by-rule verdict

| Rule | Would-ship-in-ruff? | Taxonomy fit | Default-on safety | One-sentence reason |
|---|---|---|---|---|
| CMT-001 | YES | CLEAN | RISKY | Commented-out code is a well-known smell, but pure-regex/heuristic detection is famously noisy on docstrings and pseudo-code snippets. |
| CMT-002 | YES | CLEAN | SAFE | Block-length and line-length thresholds with configurable limits are a textbook ruff-style rule. |
| CMT-005 | MAYBE | CLEAN | UNSAFE | "Restates the next line" is fundamentally semantic and ships marked EXPERIMENTAL, ruff would only ship behind a preview gate. |
| PROSE-001 (comments) | MAYBE | AMBIGUOUS | SAFE | Em-dash ban in code comments is a niche house style; harmless because opt-in, but the code lives in two modules sharing one rule code. |
| PROSE-003 (comments) | MAYBE | AMBIGUOUS | SAFE | Same shape as PROSE-001: opt-in and safe, but rule-code reuse across `comments` and `prose` blurs the taxonomy. |
| TERM-NNN | YES | CLEAN | SAFE | A "configure your forbidden vocabulary" mechanism modelled on ruff's name-banning rules; inert by default. |
| DRY-001 | MAYBE | CLEAN | RISKY | AST-normalized duplicate detection is valuable but precision is hard; 5-statement threshold will hit fixture/mapper boilerplate. |
| SIZE-001 | YES | CLEAN | RISKY | File-length thresholds are common, but 300/500 effective-lines defaults will fire on lots of healthy modules without per-project tuning. |
| SIZE-002 | YES | CLEAN | SAFE | 50/80-line function caps mirror pylint `too-many-lines` style rules with sane defaults. |
| SIZE-003 | YES | CLEAN | RISKY | >10-method classes is a useful smell but flags many legitimate services / ORM models / view classes. |
| COMPLEXITY-001 | YES | CLEAN | SAFE | Cyclomatic complexity at 10/15 is the de-facto industry default (mccabe, ruff `C901`). |
| PARAM-001 | YES | CLEAN | SAFE | Mirrors pylint `too-many-arguments` with conventional thresholds. |
| PATH-001 | YES | CLEAN | SAFE | Pure project-invariant; inert until configured, can't misfire. |
| LAYER-001..005 | MAYBE | CLEAN | SAFE | Layer-import enforcement is great for the niche it targets, but ruff would push it to a plugin; safe because it self-disables outside the four-layer layout. |
| META-001..005 | NO | MISPLACED | SAFE | Useful internal test-suite check, but a competitor tool would surface this as `pytest`/CI infra, not as an emitted rule code in user output. |
| KWARG-001 | MAYBE | CLEAN | UNSAFE | "All multi-arg functions must use bare `*`" is an aggressive house style; will flood any project that doesn't already mandate it. |
| NAMING-001 | YES | CLEAN | RISKY | Repository-method prefixes are a common convention; safety depends on the project actually using a "repository" pattern. |
| NAMING-002 | YES | CLEAN | RISKY | Same shape as NAMING-001 for services; identical caveats. |
| NAMING-003 | YES | CLEAN | SAFE | Warning-level HTTP-verb match is sensible and ships at the right severity. |
| NAMING-004 | YES | CLEAN | RISKY | Boolean-prefix heuristic is fine as a warning, but "is this function boolean?" detection is error-prone without return-type inference. |
| IMPORT-001 | YES | CLEAN | RISKY | Inline-import ban is a defensible style rule (matches ruff `PLC0415`) but breaks legitimate lazy-import and circular-import workarounds. |
| TYPING-001 | MAYBE | AMBIGUOUS | UNSAFE | "No `TYPE_CHECKING` outside model files" inverts the community consensus (ruff `TCH` actively *promotes* `TYPE_CHECKING` guards). |
| ENDPOINT-001 | MAYBE | AMBIGUOUS | SAFE | Generic nesting-depth warning bolted onto an "endpoint" concept; nesting depth should be a generic rule, not endpoint-scoped. |
| PORT-001..003 | MAYBE | CLEAN | SAFE | Architecture-specific; valuable on projects that adopt ports & adapters, inert elsewhere. |
| PROSE-001 (md) | YES | AMBIGUOUS | SAFE | Opt-in markdown lint; rule-code shared with the `comments` module (see Taxonomy). |
| PROSE-002 | MAYBE | CLEAN | SAFE | British-spelling enforcement is the kind of opinionated rule competitor tools usually leave to vale/textlint. |
| PROSE-003 (md) | YES | AMBIGUOUS | SAFE | Same as PROSE-001 (md). |
| AUTH-001 | YES | CLEAN | RISKY | "Mutation endpoints must have auth" is great, but FastAPI-shaped detection will misfire on Flask / Django / Starlette routers. |
| SQL-001 | YES | CLEAN | RISKY | Raw-SQL detection is standard (ruff `S608` family) but pattern matching catches docstring examples and migration files. |
| SECRET-001 | YES | CLEAN | RISKY | Secret scanning belongs in every linter, but pattern-based detection without entropy / context analysis is notoriously noisy. |
| JUNK-001 | YES | CLEAN | SAFE | Conservative pattern list and an `allow` glob — exactly how a default-on hygiene rule should be shaped. |
| JUNK-002 | YES | CLEAN | RISKY | "Image/binary outside an asset dir" depends on the project having an asset convention; will flood many projects. |
| STALE-001 | YES | CLEAN | SAFE | Inert until configured; clean targeted use case. |
| TYPE-001 | YES | CLEAN | RISKY | Catches real smells but `dict[str, Any]` legitimately appears at JSON boundaries; needs a `boundary_dict` escape that the docstring hints at but isn't implemented. |
| TYPE-002 | YES | CLEAN | SAFE | Bare-container annotations are unambiguously bad; ruff `UP006` / `FA100` cover similar ground. |
| TYPE-003 | YES | CLEAN | SAFE | `**kwargs: Any` ban with `Unpack[TypedDict]` exception is exactly right. |
| TEST-001 | YES | CLEAN | RISKY | "Every production module has a test" is a useful nudge, but path-matching coverage will misfire on any non-canonical test layout. |
| AAA-001 | MAYBE | CLEAN | UNSAFE | Comment-marker enforcement is an extremely opinionated style; will flag the vast majority of real pytest suites on day one. |
| AAA-002 | MAYBE | CLEAN | RISKY | Shared arrange-prefix detection is a clever DRY rule, but parametrize / fixture-resistant tests with identical setup are normal. |

Counts (excluding `TERM-NNN`, counting the two PROSE-001 / PROSE-003 entries
once each since they share a rule code):
- YES = 21, MAYBE = 13, NO = 1 (META, treated as a single block).
- SAFE = 19, RISKY = 14, UNSAFE = 4.

## 2. Taxonomy review

**Prefixes carrying two intents**

- `PROSE-001` and `PROSE-003` are *emitted by two different checks* (`comments`
  and `prose`) with overlapping semantics. The output is ambiguous: a user
  ignoring `PROSE-001` silences both the markdown rule and the code-comment
  rule, even though they have different audiences. **Structural**: split into
  `CMT-003` / `CMT-004` (or `PROSE-C-001`) for the comment-side, keep
  `PROSE-001` for prose files.
- `CMT-*` mixes hygiene (CMT-001/002) with experimental semantic analysis
  (CMT-005). **Cosmetic**: give CMT-005 a preview-gate prefix (e.g. `CMTX-`)
  the way ruff uses `PLR` vs `PLC` to separate maturity.
- `NAMING-*` carries two different intents: identifier-prefix conventions
  (NAMING-001/002/004) and HTTP-verb matching (NAMING-003). **Cosmetic**:
  rename NAMING-003 to e.g. `HTTP-001` so the prefix matches the audience.

**Intent split across two prefixes**

- DRY enforcement lives in both `DRY-001` (duplication) and `AAA-002` (test
  arrange-prefix duplication). One prefix for "duplicated structure"
  (`DUP-*`) and one for "test-style" (`AAA-*`) would be cleaner. **Cosmetic.**
- "File-shape" rules are in both `SIZE-*` (lines, methods) and
  `COMPLEXITY-*` and `PARAM-*` — three prefixes for one concept ("function
  is too big"). Ruff would collapse these under a single prefix
  (`PLR` / `C9`) with sub-codes. **Cosmetic.**
- "Architecture invariant" intent is split across `LAYER-*`, `PORT-*`,
  `PATH-*`. Defensible because the *mechanisms* differ, but a user reading
  the rule list won't intuit that. **Cosmetic.**
- `IMPORT-001`, `TYPING-001`, `ENDPOINT-001` are bundled under one module
  (`pattern_divergence`) but emit three unrelated prefixes. **Cosmetic** —
  the prefixes are fine, but the module name is unhelpful.

**Naming the rule code that doesn't fit**

- `META-*` reads like a self-test that escaped into the user-facing taxonomy.
  Ruff would not emit `META-*` codes on a user's project; it would run them
  as an internal invariant. **Structural**: hide from `lanorme check`,
  expose via `lanorme self-check`.

## 3. Ergonomics review

**What works**
- Hierarchical select/ignore by code *and* category (`--select TYPE,AUTH`)
  is the right shape; matches ruff's mental model.
- `pyproject.toml` discovery with walk-up, dedicated `lanorme.toml`
  precedence, plus CLI override is exactly the expected layering.
- Per-check tables in TOML (`[tool.lanorme.stray_artifacts]`) are
  discoverable and idiomatic.
- Plugin entry-point group plus explicit `plugins = [...]` is good.
- Zero runtime deps and `uvx`-from-wheel ergonomics are a real
  differentiator.

**What's missing or weak**

1. **Inline suppression coverage**. KWARG-001 documents `# noqa: KWARG-001`
   but the README does not document `# noqa` at all, and there is no
   evidence (in the docstrings I'm allowed to read) that it works
   uniformly across every check. A ruff-class tool needs `# noqa`,
   `# noqa: CODE1,CODE2`, and file-level `# lanorme: noqa` to be
   first-class and uniform.
2. **Per-file ignores**. No `[tool.lanorme.per-file-ignores]` table is
   documented. This is the single most-used ruff feature.
3. **Severity overrides**. Severities (warn vs error) are hard-coded into
   each check (NAMING-003 "warning", SIZE-001 "warn at 300, error at 500").
   A user who wants to demote `SECRET-001` to a warning in tests has no
   knob; ditto a user who wants to promote NAMING-003 to error.
4. **Autofix**. The `Violation` schema carries a `fix` field, but the README
   shows no `lanorme check --fix`. Half the value of ruff is `--fix` and
   `--unsafe-fixes`.
5. **Output formats**. README lists `--output-format json`. No mention of
   `text`, `github`, `gitlab`, `sarif`, `junit`, `concise`, `grouped`. CI
   integration needs at least `github` annotations and `sarif`.
6. **Severity / exit-code policy**. Exit is `1` if any check fails. No
   `--exit-zero`, no `--exit-non-zero-on-fix`, no separation between
   warnings and errors in the exit code.
7. **Caching**. No mention of a cache. ruff's speed story rests on caching
   per-file results; on a large repo, every-file AST parsing across ~20
   checks will be slow without it.
8. **Rule discoverability**. `lanorme rules` lists rules but there is no
   `lanorme rule <CODE>` to dump the rationale, examples, and config knobs
   the way `ruff rule E501` does.
9. **Per-check config is not introspectable**. There is no way to see what
   knobs a check accepts without reading the source. `lanorme rule
   stray_artifacts` should print the table schema.
10. **Discovery of which checks fired**. JSON output is mentioned but no
    schema is documented in the README, so CI integration requires reading
    code.

## 4. Rule-design pitfalls (noisiest defaults)

**Most likely to be ignored project-wide on day one**

1. **KWARG-001** — Forcing every multi-arg function to use bare `*` is an
   extreme position. Most Python projects won't accept this.
2. **AAA-001** — Requiring "# Arrange / # Act / # Assert" markers in test
   bodies will fire on every existing pytest suite in the wild.
3. **TYPING-001** — Banning `TYPE_CHECKING` guards in non-model files
   contradicts ruff's `TCH` family, which actively recommends them. Will
   produce thousands of findings on a typed codebase.
4. **CMT-001** — Commented-out-code detection is notorious for flagging
   docstring examples, table-of-contents blocks, and ASCII art.
5. **SECRET-001** and **SQL-001** — Pattern-based detection without
   entropy/context heuristics produces lots of false positives on real
   repos (config schemas, test fixtures, ORM definitions).
6. **JUNK-002** — On a project with no "assets directory" convention,
   every PNG anywhere is a finding.
7. **TYPE-001** — Despite being correct, `dict[str, Any]` shows up at
   every JSON boundary; without a working `@boundary_dict` escape, this
   will be ignored.

**Will fail open vs hard**

- The "inert until configured" pattern (`PATH-001`, `STALE-001`,
  `TERM-NNN`, `LAYER-*` when layout absent, `PORT-*` when layout absent)
  is **fail-open by design** and well-considered.
- `META-*` will **fail hard** on third-party checks that don't conform —
  a plugin author shipping a slightly malformed check will see their
  users' CI break with a `META-*` code that points at *their* check.
  This is the wrong default; META should produce a warning, not block.
- Most other checks fail hard (exit 1) with no way to demote (see
  ergonomics gap 3).

## 5. Overall verdict

**Ship-with-changes**, not ship-as-is. The taxonomy is mostly clean and
the architecture (plugin entry points, per-check TOML tables, walk-up
config discovery, zero deps) is competitive with ruff. But several
defaults are too opinionated for a "point it at any project" tool, and
the ergonomics floor (no per-file-ignores, no severity overrides, no
autofix, no cache, no `rule <CODE>` introspection, no documented `# noqa`
story) is below what a default-on linter in 2026 needs to clear.

**Top-3 ergonomic gaps**: (1) per-file-ignores table; (2) severity
override / promote-demote knobs; (3) uniform `# noqa: CODE` story
documented in README, plus `lanorme rule <CODE>` introspection.

**Top-3 rules needing precision work before going default-on**:
KWARG-001, AAA-001, TYPING-001 (the last needs its premise re-examined
against the ruff `TCH` consensus).
