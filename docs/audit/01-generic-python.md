# LaNorme audit — generic mainstream Python OSS perspective

Reviewer scope: a senior maintainer looking at LaNorme as a candidate linter
for a randomly chosen mainstream Python OSS project (CLI tools, libraries,
small web apps, data scripts). Judgements are based only on the README,
each check's top module docstring, and `lanorme rules` output.

## Rule-by-rule verdict

| Rule | Applicability | Soundness | Default verdict | Reason |
|---|---|---|---|---|
| CMT-001 | UNIVERSAL | BORDERLINE | KEEP-ON | Commented-out code is a near-universal smell, but AST/regex detection is famously noisy on doctest-y or example-heavy comments. |
| CMT-002 | UNIVERSAL | SOUND | KEEP-ON | Length limits on comment blocks/lines are a benign, easily tunable hygiene rule. |
| CMT-005 | CONDITIONAL | QUESTIONABLE | KEEP-OPT-IN | "Restates the next line" is inherently fuzzy and the docstring itself labels it EXPERIMENTAL; default-off is correct. |
| PROSE-001 (comments) | DOMAIN | QUESTIONABLE | KEEP-OPT-IN | Banning em dashes in *code comments* is a stylistic preference, not a hygiene rule. |
| PROSE-003 (comments) | CONDITIONAL | BORDERLINE | KEEP-OPT-IN | Some teams welcome emoji in comments/docstrings; opt-in is right. |
| TERM-NNN | DOMAIN | SOUND | KEEP-OPT-IN | Project-specific vocabulary enforcement; inert by default is the correct posture. |
| DRY-001 | CONDITIONAL | BORDERLINE | KEEP-ON | AST-normalized dup detection at >=5 statements is reasonable, but false positives on trivial CRUD/getters/validators are a known pain point. |
| SIZE-001 | UNIVERSAL | SOUND | KEEP-ON | 300/500 effective-line file thresholds are mainstream and easily tuned. |
| SIZE-002 | UNIVERSAL | SOUND | KEEP-ON | 50/80 line function ceilings overlap pylint's `too-many-lines` family and are widely accepted. |
| SIZE-003 | CONDITIONAL | BORDERLINE | KEEP-ON | 10-method ceiling is aggressive for OSS libraries that expose rich classes (e.g. clients, models). |
| COMPLEXITY-001 | UNIVERSAL | SOUND | KEEP-ON | Cyclomatic complexity 10/15 mirrors mccabe / ruff C901 defaults. |
| PARAM-001 | UNIVERSAL | SOUND | KEEP-ON | 5/8 parameter ceiling matches pylint's `too-many-arguments` default region. |
| PATH-001 | DOMAIN | SOUND | KEEP-OPT-IN | Useless without configuration; inert default is correct. |
| LAYER-001..005 | DOMAIN | SOUND | KEEP-OPT-IN | Hexagonal-architecture-specific; mainstream OSS projects rarely use `domain/ application/ infrastructure/ api/`. Naturally inert is fine. |
| META-001..005 | DOMAIN (linter-internal) | SOUND | KEEP-ON | Self-validation of registered checks; harmless and useful for plugin authors. |
| KWARG-001 | CONDITIONAL | QUESTIONABLE | KEEP-OPT-IN | Forcing bare-`*` on every multi-arg function is a strong house style, not a community norm; will be very noisy on libraries with stable positional APIs. |
| NAMING-001 | DOMAIN | BORDERLINE | KEEP-OPT-IN | Assumes a Repository pattern and a fixed CRUD verb set; mostly relevant to DDD/hexagonal codebases. |
| NAMING-002 | DOMAIN | BORDERLINE | KEEP-OPT-IN | Same as NAMING-001 but for service classes. |
| NAMING-003 | DOMAIN | BORDERLINE | KEEP-OPT-IN | FastAPI/HTTP-specific; only meaningful in web codebases. |
| NAMING-004 | UNIVERSAL | BORDERLINE | KEEP-ON | `is_/has_/can_/should_` prefixes for booleans are PEP 8-adjacent; warning level is appropriate. |
| IMPORT-001 | CONDITIONAL | QUESTIONABLE | KEEP-OPT-IN | Inline imports are a legitimate tool (cycle breaking, optional deps, slow imports); ruff's PLC0415 exists but is opt-in for a reason. |
| TYPING-001 | DOMAIN | QUESTIONABLE | KEEP-OPT-IN | Banning `if TYPE_CHECKING:` outside "model files" inverts the standard typing guidance; the common advice is to *prefer* it. |
| ENDPOINT-001 | DOMAIN | SOUND | KEEP-OPT-IN | Web-framework specific; nesting depth limit is sensible but only inside web handlers. |
| PORT-001..003 | DOMAIN | SOUND | KEEP-OPT-IN | Hexagonal-only; inert in absence of `application/ports/` is correct. |
| PROSE-001 (md) | CONDITIONAL | BORDERLINE | KEEP-OPT-IN | House-style rule; opt-in default is right. |
| PROSE-002 | CONDITIONAL | QUESTIONABLE | KEEP-OPT-IN | British-spelling enforcement is a strong stylistic choice; most OSS projects standardise on US English. |
| PROSE-003 (md) | CONDITIONAL | BORDERLINE | KEEP-OPT-IN | Same as PROSE-001; opt-in is correct. |
| AUTH-001 | DOMAIN | SOUND | KEEP-OPT-IN | FastAPI-shaped; valuable where applicable, irrelevant elsewhere. The README lists `security_patterns` as "always on" which is too aggressive for non-web projects. |
| SQL-001 | CONDITIONAL | BORDERLINE | KEEP-ON | Catching raw SQL string literals is high-value security but false-positives on legitimate SQL utilities, migrations, analytics scripts. |
| SECRET-001 | UNIVERSAL | SOUND | KEEP-ON | Hardcoded-secret detection is a no-brainer for any codebase. |
| STALE-001 | CONDITIONAL | SOUND | KEEP-OPT-IN | Useful after a refactor; inert without configuration. |
| JUNK-001 | UNIVERSAL | SOUND | KEEP-ON | Scratch/OS junk detection is benign and well scoped. |
| JUNK-002 | CONDITIONAL | BORDERLINE | KEEP-OPT-IN | Flagging any image/binary outside an asset directory will fire on test fixtures, ML datasets, notebooks, sample data; default-on is too aggressive. |
| TYPE-001 | CONDITIONAL | BORDERLINE | KEEP-OPT-IN | Banning `dict[str, Any]` at boundaries is a strong typing opinion; overlaps ruff `ANN401`. Useful in app code, hostile to JSON/config-heavy libs. |
| TYPE-002 | UNIVERSAL | SOUND | KEEP-ON | Bare `dict`/`list`/`tuple`/`set` annotations are universally discouraged; overlaps pyupgrade/UP006 territory. |
| TYPE-003 | CONDITIONAL | SOUND | KEEP-ON | Typed `**kwargs` via `Unpack[TypedDict]` is now the mainstream recommendation. |
| TEST-001 | CONDITIONAL | QUESTIONABLE | KEEP-OPT-IN | "Every production module has a matching `test_*.py`" is a structural assumption many sound test suites violate (integration-first, behaviour-grouped, snapshot tests). |
| AAA-001 | DOMAIN | QUESTIONABLE | KEEP-OPT-IN | Mandatory Arrange/Act/Assert *comment markers* is a strong house style. Most pytest codebases rely on blank-line separation, not comments. |
| AAA-002 | CONDITIONAL | BORDERLINE | KEEP-OPT-IN | DRY-of-arrange-prefix conflicts with pytest's parametrize/fixture idioms and the common practice of explicit, repeated setup for readability. |

## Missing rules

A ruff/pylint/flake8 user would expect, but LaNorme lacks:

1. **Unused imports / unused variables / undefined names** (pyflakes F401, F841, F821) — the bread and butter of Python linting.
2. **PEP 8 naming and formatting** (snake_case, PascalCase, line length, indentation) — covered by ruff E/W/N rules.
3. **Mutable default arguments** (B006) and other `flake8-bugbear` core anti-patterns (e.g. `except:` bare, useless comparisons).
4. **`print()` / `pdb` / debug-statement detection** (T201, T203) — extremely common hygiene in libraries.
5. **TODO/FIXME tracking** with author/ticket requirements — a near-universal expectation that LaNorme covers only in comment style, not lifecycle.
6. **Deprecated-API usage / pyupgrade-style modernisations** (e.g. `Optional[X]` → `X | None`, f-string conversions).
7. **Missing docstrings on public API** (pydocstyle D-series) — LaNorme has no docstring presence rule despite scrutinising their content.

## Suspect rules (intent-level concerns)

- **TYPING-001** (no `if TYPE_CHECKING:` outside "model files"). The mainstream typing community *encourages* `TYPE_CHECKING` guards to avoid circular imports and runtime cost. Inverting that for arbitrary directories is unusual.
- **KWARG-001** (force bare-`*` on every multi-arg function). Defensible house style; not a community norm. Will produce thousands of findings on a typical library.
- **NAMING-001/002** with a hardcoded CRUD verb set (`get_/create_/update_/delete_/list_`). Excludes legitimate domain verbs (`find_`, `fetch_`, `archive_`, `publish_`, `materialize_`).
- **AAA-001** demanding *comment* markers in tests. Reasonable people disagree; the more common convention is blank-line separation, which this very check *replaced* (per the `TEST-002` deprecation note).
- **PROSE-002** (mandatory British spelling). Reasonable as opt-in; would be hostile if ever defaulted on.
- **JUNK-002** as currently scoped (any binary outside an asset dir). Reasonable for service code, painful for ML/data projects.
- **CMT-005** is self-described as experimental; agreed.

## Overlap with established tools

- **TYPE-002** overlaps ruff `UP006`/`FA100` (modern generics) and mypy's `disallow-any-generics`. Justified only if LaNorme is meant to be a standalone linter; otherwise redundant.
- **TYPE-001** overlaps ruff `ANN401` (`Any` ban). LaNorme's framing (boundary-only, with exemptions) is slightly more nuanced, which justifies coexistence.
- **TYPE-003** overlaps `ANN003` (missing `**kwargs` annotation) but goes further by banning `Any`. Justified.
- **COMPLEXITY-001** duplicates ruff/mccabe `C901`. Not justified — strictly redundant with a more battle-tested implementation.
- **SIZE-002 / PARAM-001 / SIZE-003** duplicate pylint's `too-many-lines` / `too-many-arguments` / `too-many-public-methods`. Pylint already does this; LaNorme adds nothing technical.
- **IMPORT-001** duplicates ruff `PLC0415`. Not justified.
- **SECRET-001** overlaps `detect-secrets`, `gitleaks`, ruff `S105`/`S106`. Justified only if LaNorme's patterns are curated; otherwise the dedicated tools win.
- **SQL-001** overlaps `bandit` B608 (sql_injection). Mostly redundant.
- **CMT-001** overlaps ruff `ERA001` (eradicate). Largely redundant.
- **PROSE-002 / PROSE-003** overlaps Vale, markdownlint. Not justified for a Python linter to own.

The net pattern: LaNorme's *structural-architecture* and *project-invariant*
checks (LAYER, PORT, PATH, STALE, TERM, JUNK, TEST-001) are genuinely novel
contributions. Its *code-level* checks (TYPE, SIZE, COMPLEXITY, PARAM,
IMPORT, SECRET, SQL, CMT-001) re-implement well-trodden ground and would be
better delegated to ruff + bandit, with LaNorme focusing on the architectural
layer it owns.

## Overall verdict

On a *random mainstream Python OSS project* (typical: CLI tool, library, or
small Flask/FastAPI app, no hexagonal layout), I would **not** install
LaNorme as the primary linter — ruff + mypy + bandit cover the universal
ground better, and LaNorme's most distinctive value (LAYER/PORT/TERM/STALE)
would sit idle. I *would* install it on a project that has explicitly
adopted ports-and-adapters / DDD, where the architectural checks have no
substitute. The README's "always on" list is too aggressive: `naming_consistency`
and `security_patterns` (AUTH-001) are domain-specific, not universal.

Top-5 most valuable: SECRET-001, JUNK-001, SIZE-001, TYPE-003, STALE-001.
Top-5 most likely to be turned off: KWARG-001, AAA-001, TYPING-001,
NAMING-001/002, TEST-001.
