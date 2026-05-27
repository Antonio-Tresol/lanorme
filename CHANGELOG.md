# Changelog

All notable user-facing changes to LaNorme. The public API is the set of
rule codes that may appear in `select` / `ignore` / `per-file-ignores`
and the configuration keys under `[tool.lanorme]`. See the Versioning
section in the README for the breaking-change policy.

This project follows the spirit of [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

## [0.2.0]

### Added

- `lanorme rule <CODE>` CLI subcommand. Prints the matching section of
  `docs/RULES.md` (bundled into the wheel) for one rule code; exits 2
  with a helpful pointer if the code is unknown.
- Project metadata for distribution: `authors`, `[project.urls]`
  (homepage / repository / issues / changelog), `Development Status ::
  4 - Beta`, Python 3.14 classifier, `Typing :: Typed`, additional
  keywords.
- `[dependency-groups] dev = ["pytest>=8"]`: contributors install with
  `uv sync --group dev` and run the unit suite with
  `uv run pytest tests/unit`.
- `[tool.hatch.build.targets.sdist]` selects the publishable artefacts
  (src, README, CHANGELOG, LICENSE, docs/RULES.md, pyproject) for the
  source distribution.
- `security_calls` check, six default-on dangerous-call rules, each one
  AST node and precision-first: `SHELL-001` (subprocess `shell=True`,
  `os.system`, `os.popen`), `DESERIAL-001` (pickle / marshal / dill /
  `yaml.load` without `SafeLoader`), `EVAL-001` (`eval` / `exec` /
  `compile` on a non-literal first argument), `CRYPTO-001` (`md5` / `sha1`
  used for security, deprecated TLS protocol constants), `TLS-001`
  (`verify=False` in `requests` / `httpx` / `aiohttp`, `ssl.CERT_NONE`,
  `ssl._create_unverified_context`), `DEBUG-001` (`Flask` / `FastAPI`
  constructors and `app.run` calls with `debug=True`, `DEBUG = True` at
  module scope in `*settings.py` / `*config.py`).
- `[tool.lanorme.per-file-ignores]` TOML table: map a path glob to a
  list of rule codes (full code such as `SQL-001` or a category prefix
  such as `SQL`) that should never fire for matching files.
- `# noqa` inline suppression. Bare `# noqa` silences any rule on the
  line it sits on; `# noqa: CODE1,CODE2` silences only the listed codes
  (full codes or category prefixes). Case-insensitive.
- `test_style` check with `AAA-001` (test functions must carry inline
  Arrange / Act / Assert section comments, or Given / When / Then) and
  `AAA-002` (test functions in the same file must not share an identical
  arrange prefix). Default-off; enable via
  `[tool.lanorme.test_style] enabled = true`.
- `CHANGELOG.md`: `docs/RULES.md` per-rule reference, versioning policy
  in README.

### Changed (breaking)

- **Rule renames** so each rule's code matches its actual scope:
  - `AUTH-001` &rarr; `AUTHN-001` (the check verifies authentication
    presence; it does not measure authorisation).
  - `TEST-001` &rarr; `TESTFILE-001` (it verifies that a `test_*.py`
    partner exists; it does not measure coverage).
  - `SECRET-001` &rarr; `SECRETPY-001` (Python-source scope only;
    `.env` / `*.yaml` / `*.ipynb` are out of scope until a future
    `SECRET-002` / `SECRET-003` lands).
- **Default demotions** based on the multi-reviewer audit
  (`docs/audit/SUMMARY.md`). All previously default-on, now opt-in:
  - `NAMING-001` (repository CRUD prefixes). Opt-in via
    `[tool.lanorme.naming_consistency] repo_crud = true`.
  - `NAMING-002` (service CRUD prefixes). Opt-in via
    `service_crud = true`. These two rules actively conflicted with
    `TERM-NNN` on a serious DDD project; the audit's biggest single
    finding.
  - `KWARG-001` (`bare *` on every multi-argument function). Opt-in
    via `[tool.lanorme.named_args] enabled = true`.
  - `AAA-001` / `AAA-002`. Opt-in via
    `[tool.lanorme.test_style] enabled = true`.
- **Earlier rename pass** (commit `4703490`):
  - `SEC-001` &rarr; `AUTH-001` (later renamed again, see above).
  - `SEC-002` &rarr; `SQL-001`, `SEC-003` &rarr; `SECRET-001` (later
    renamed again, see above).
  - `SIZE-004` &rarr; `COMPLEXITY-001` (cyclomatic complexity is not a
    size).
  - `SIZE-005` &rarr; `PARAM-001` (parameter count is not a size).
  - `PATTERN-001` &rarr; `IMPORT-001`, `PATTERN-002` &rarr; `TYPING-001`
    (later removed), `PATTERN-004` &rarr; `ENDPOINT-001`.
  - `PROJ-001` &rarr; `PATH-001`.
  - `ART-001` / `ART-002` &rarr; `JUNK-001` / `JUNK-002`.
  - `NAMED-001` &rarr; `KWARG-001`.
- **CMT-003 / CMT-004 unified under PROSE-001 / PROSE-003** (one rule
  code per intent regardless of file type). The `comments` check now
  emits `PROSE-001` and `PROSE-003` on Python comments and docstrings
  when `em_dash` / `emoji` are enabled; the `prose` check still emits
  the same codes on Markdown.

### Removed (breaking)

- `TEST-002` (weak blank-line AAA heuristic). Superseded by `AAA-001`
  (comment-marker AAA in the `test_style` check, stronger signal).
- `TYPING-001` (no `TYPE_CHECKING` outside model files). Three of four
  reviewers in the audit flagged the rule's premise as inverting the
  community typing consensus (ruff's `TCH` family actively promotes
  `TYPE_CHECKING` guards). The helper was also unwired in practice. May
  return as an opt-in with the premise inverted (encourage rather than
  forbid).

## [0.1.0] - initial commit `aaef1f5`

First public-shape release. Eighteen checks extracted from a private
codebase, fully de-identified, with a configurable CLI (`lanorme check`,
`lanorme rules`), TOML-driven configuration (`[tool.lanorme]` in
`pyproject.toml` or a dedicated `lanorme.toml`), and a plugin model
through `[project.entry-points."lanorme.checks"]` or
`[tool.lanorme] plugins = [...]`.
