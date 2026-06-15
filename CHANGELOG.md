# Changelog

All notable user-facing changes to LaNorme. The public API is the set of
rule codes that may appear in `select` / `ignore` / `per-file-ignores`
and the configuration keys under `[tool.lanorme]`. See the Versioning
section in the README for the breaking-change policy.

This project follows the spirit of [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

## [0.13.0]

### Added

- A versioned **documentation site** at
  [lanorme.github.io/lanorme](https://lanorme.github.io/lanorme/) (mkdocs-material
  with search and `mike` version switching), built to be read by agents as well as
  people. Every page is also served as raw Markdown at its `.md` URL, with
  `llms.txt` / `llms-full.txt` indexes and a generated JSON Schema
  (`lanorme.schema.json`) for editors and agents. The configuration reference, rule
  index, schema and llms files are generated from the tool, with a CI sync test so
  they cannot drift.
- A warning **baseline** for adopting LaNorme on an existing codebase. `lanorme
  baseline write` records the current findings to `lanorme-baseline.json`; with
  `[tool.lanorme] baseline = "lanorme-baseline.json"` set, those findings are
  suppressed and only new ones report (and compose with `promote`). Matching is
  content-anchored, so an entry survives edits above it; a recorded warning never
  suppresses a finding that has escalated to error-tier; and a per-key count
  guarantees new debt always surfaces. `lanorme check --no-baseline` reports the
  whole debt and `lanorme baseline status` lists stale entries. See the
  "Adopting on an existing codebase" tutorial.
- An opt-in **`docs` check (DOCS-001..008)**: a Markdown-structure standard for a
  documentation tree. One H1, no skipped heading levels, a canonical skimmer line
  and image alt text are errors; preferring SVG or Mermaid over a raster image, a
  section index, a home in the architecture, and no hand-numbered headings are
  warnings.
- **PROSE-004** (opt-in, advisory): an em-dash density detector. Em dashes are
  allowed at the density of natural edited English and only sustained overuse is
  flagged; a `docs/` region can swap the outright em-dash ban (PROSE-001) for this
  density rule.

### Changed

- NAMING-004 no longer fires on boolean `@property` / `@cached_property` /
  `@staticmethod` accessors or on `Protocol` members, and its fix suggestion
  strips a leading verb (so `check_auth_posture` suggests `is_auth_posture`).
- SIZE-002 counts effective (non-blank, non-comment) lines for a function,
  matching SIZE-001, so adding an explanatory comment cannot push a function
  over the limit.
- The README now points to the documentation site instead of duplicating the
  configuration, profiles and rule reference; the repository homepage links there
  too.
- Heuristic-accuracy evaluations moved to a dedicated `evals/` directory (the
  per-rule scorers, their labelled corpora, and a commit-stamped release audit in
  `evals/results/`), leaving `benchmarks/` for performance only. A
  contributor-facing reorganisation; no rule or CLI change.

### Fixed

- TESTFILE-001 missed production modules whose imports appeared only inside
  import-like strings; it now resolves imports from the AST. A repository can see
  new TESTFILE-001 warnings it did not before (and, under a profile that promotes
  them to errors, a build that newly fails): this is why the release is a minor.
- PROSE-001 / PROSE-002 false positives inside double-backtick inline code spans.
- STALE-001 false positive on a `#` inside a string literal (the scan is now
  tokenize-based).
- PORT-002 false positive on `from <ports_pkg> import <module>` adapter imports;
  PORT-003 false negative on attribute-form instantiation in `api/`.
- LAYER-002 false positive on a third-party submodule named like a layer.
- PATH-001 vendor exclusion matched substrings rather than whole path segments.
- TERM-001 double-fired on bare assignment targets.

## [0.12.0]

### Added

- Config profiles via `[tool.lanorme] extends`. Adopt a shipped preset by name,
  or a local `.toml` by path, and its keys merge underneath your own (local
  always wins). Bundled profiles: `strict` (turns on every opt-in check and
  promotes all warnings to errors) and the architecture presets `hexagonal`,
  `clean`, and `layered` (preset `layer_deps` boundaries, and ports-and-adapters
  coverage for `hexagonal`). Compose them, for example
  `extends = ["strict", "hexagonal"]`. Closes #19.

- Promote advisory warnings to build-failing errors with `[tool.lanorme] promote`
  (or `--promote`). List a rule code, a category, or `ALL`, and matching
  warnings become violations that fail the run. This lets heuristic rules ship
  as non-breaking warnings by default while a project that wants them enforced
  opts into a hard stop. Promotion runs last, so a warning already silenced by
  `ignore`, `per-file-ignores`, or `# noqa` is never promoted.

- `TYPE-004` in the `strong_types` check: an advisory warning when a function
  has at least one annotated parameter and returns a real value in its own
  scope but declares no return type. It is the high-signal completeness subset
  of ruff's `ANN` family (it fires only when the inputs are already typed and a
  value escapes), so fully untyped functions and value-less procedures are left
  alone. Generators are exempt, and returns inside a nested `def` or `lambda`
  do not count. Ships as a warning, not a build failure, because presence
  enforcement is noisier than the weak-type rules.

## [0.11.0]

### Added

- A `github` output format (`--output-format github`) that emits GitHub Actions
  workflow commands, so findings appear inline on the PR diff. It is auto-detected
  when `GITHUB_ACTIONS` is set, unless an explicit `--output-format` is given. The
  annotation `title` uses the rule code (`DRY-001`) and the message is escaped, so
  a rule description or a multi-line message cannot corrupt the annotation
  (closes #4).
- `layer_deps`: a `transport_layers` key under `[tool.lanorme.layer_deps]`.
  Hexagonal apps often have several peer transport adapters with identical
  import rules (a REST `api/`, an `mcp_server/`, a `grpc_server/`). Listing them
  in `transport_layers` extends the composition-root exception, previously
  hard-wired to `api/`, to each peer, so a non-api transport's wiring file may
  import `infrastructure/`. Defaults to `["api"]`, so existing projects are
  unaffected. A peer must also appear in `layers` and be given an `allowed`
  entry.
- `LAYER-006`: an advisory **warning** when a `transport_layers` entry is not
  among the configured `layers` (and therefore has no effect).

### Fixed

- `CMT-001` no longer flags [PEP 723](https://peps.python.org/pep-0723/) inline
  script metadata as commented-out code. A line such as
  `# dependencies = ["rich"]` inside a `# /// script` ... `# ///` block parses as
  an assignment and was reported as dead code; the block is tooling metadata, so
  its lines are now exempt (a closing `# ///` fence is required, and genuine
  commented-out code elsewhere in the file is still flagged).

## [0.10.0]

### Added

- Cascading per-directory config for gradual adoption (issue #28). A
  `lanorme.toml` (or `pyproject.toml` `[tool.lanorme]`) in a subdirectory now
  governs the files beneath it, even when the run starts at the repository root.
  A nested config inherits its parent and overrides only the keys it sets;
  `root = true` ends the cascade so a subtree can stand alone. File-level checks
  resolve under the config of each file's nearest enclosing region; the
  whole-tree checks (`duplication`, `test_coverage`, `layer_deps`,
  `port_coverage`, `meta`) and the run-level filters (`select` / `ignore` /
  `exclude` / `per-file-ignores`) stay anchored to the root config. A run with
  no nested config is unchanged, so existing projects keep today's behaviour.

### Changed

- A `lanorme.toml` (or `pyproject.toml` `[tool.lanorme]`) in a subdirectory is
  now honoured as a region governing that subtree. Config discovery previously
  only walked up from the target, so such a nested file was ignored; if you have
  a dormant one below your scan root, it now takes effect. This is why the
  release is a minor, not a patch.

## [0.9.1]

### Fixed

- A bug in one check can no longer abort the whole run. Each check is isolated:
  if it raises, the failure is reported as a `RUN-000` warning on that check and
  every other check still runs and reports. Previously a single pathological
  file (one that overflowed a recursive helper) crashed the entire `lanorme
  check` and discarded every result.
- A subset target (a single file, or a subdirectory) now honours `exclude`,
  `per-file-ignores`, and `# noqa` that are written relative to the project root.
  Findings were relativised against the scanned directory, so those root-relative
  patterns silently stopped matching; finding paths are now re-anchored to the
  project (config) root before filtering and display.
- `security_patterns`, `strong_types`, and `pattern_divergence` no longer crash
  the run on a deeply nested file (a long operator chain, a deep union
  annotation, or a deep attribute chain). Each skips the file with a `SQL-000`,
  `TYPE-000`, or `ENDPOINT-000` warning, matching `DRY-001`; the `comments` check
  likewise tolerates a deeply nested expression in a comment.

### Internal

- Backfilled unit tests for previously untested default-on checks (`secrets`,
  `file_limits`, `security_patterns`, `strong_types`, `pattern_divergence`,
  `comments`), taking the suite from 103 to 156 tests.
- `DRY-001` (duplication) no longer crashes the whole run on a deeply nested
  file. Normalising a function body deep-copies its AST, which overflowed the
  recursion limit and raised `RecursionError` on a pathological file; the file
  is now skipped with a `DRY-000` warning, mirroring how `SIMILAR-001` already
  guards itself. Surfaced when a single-file target walks a large surrounding
  directory.
- `lanorme check <file.py>` (a single-file target, or any subset of paths
  narrower than a directory) silently reported zero findings while
  `lanorme check <dir>` on the same tree fired (issue #17). Every tree-walking
  check iterates a directory, and `os.walk` over a file yields nothing, so the
  scan found no files at all. A file or multi-path target is now walked through
  its surrounding directory (so cross-file checks see the same directory scope a
  directory target already gives them), and the findings are narrowed back to
  the requested paths. A lone directory target is unchanged. Passing multiple
  paths now checks all of them rather than only the first, and a path that does
  not exist still exits `2`. Note: the layout-aware checks (`layer_deps`,
  `port_coverage`, `test_coverage`) classify by directory layout relative to the
  scan root, so they report nothing for a single-file target whose parent is not
  that layout root; run them against a directory (or pass paths that share the
  project root).

## [0.9.0]

### Changed

- `JUNK-001` (stray artifacts) now flags scratch files whose name carries a
  temp or test directory marker (`*tmpdir*`, `*tempdir*`, `*testdir*`,
  `*scratchdir*`), so the `.testdir` / `.pc_tmpdir` files a test harness leaves
  at the repo root are caught. Legitimate extension-less dotfiles such as
  `.gitignore` are unaffected. This makes a default-on rule stricter, which is
  why this is a minor release.

### Docs

- Reworked the public description of LaNorme around executable codebase
  standards: what it checks (quality, style, architecture, structure), the
  plugin interface, and gating AI-generated code. README, CONTRIBUTING, the
  package description, and the repository metadata follow the same framing.
- Documented the `x.y.z` versioning policy in the README: patch keeps every
  codebase's result unchanged, minor can newly fail a previously-passing
  codebase, major is the 1.0 stability commitment.

## [0.8.0]

### Added

- `skills` check, `SKILL-001` to `SKILL-006`: validates files named `SKILL.md`
  against the [Agent Skills specification](https://agentskills.io/specification).
  `SKILL-001` to `SKILL-003` are build failing (a well-formed `name` that matches
  its directory, a non-empty `description` within 1024 characters, and well-formed
  optional fields); `SKILL-004` to `SKILL-006` are advisory warnings (body under
  500 lines, resolving relative Markdown links, and a frontmatter that parses
  cleanly). The frontmatter parser is stdlib only and never turns its own
  uncertainty into a failure.
- `--output-format ndjson`: one JSON object per finding, newline-delimited, for
  piping into `jq`, `grep`, or `wc -l`. Each record carries `check`, `severity`
  (`error` for violations, `warning` for warnings), `code`, `rule`, `file`,
  `line`, `message`, and `fix`. A clean run emits no lines.
- `--check` now accepts a rule code or category (for example `DRY-001` or
  `SIZE`) as well as a check name. The code form runs only the owning check(s)
  and narrows the output to that code. Resolution is name first, then code or
  category, and is case-insensitive.
- A `code` field on every JSON finding (in both the `json` and `ndjson`
  formats) and on `Violation.to_dict()`, carrying the bare rule code such as
  `DRY-001`.

### Changed

- The default human output is now the `concise` format: it prints only the
  checks that found something, then a one-line summary. The previous behaviour,
  which listed every check including the passing ones, is still available as
  `--output-format full`. Exit codes are unchanged.
- The new `skills` check is on by default. It is silent on a project with no
  `SKILL.md`, but a repository that ships skills will now have them validated, so
  a non-compliant `SKILL.md` (for example a `name` that does not match its
  directory) becomes a build-failing finding on upgrade.

### Internal

- Output rendering moved out of `cli.py` into a new `lanorme.reporting` module.
  No public API change.
- Added a `docs-audit` skill and workflow that check the docs against the real
  CLI for accuracy and house style.

## [0.7.0]

### Added

- `similarity` check, `SIMILAR-001`: a fuzzy near-duplicate detector, the
  opt-in (default-off) advisory **warning** companion to the exact, build-
  failing `DRY-001`. It catches the clones `DRY-001` misses, one or two added
  statements, a reordering, a changed number, a renamed attribute or call, by
  comparing two functions on a structural token sequence (abstracting variable
  names, attribute names and numbers, scored with `difflib`) gated by anchor
  agreement on the meaning-bearing tokens `DRY-001` discards (string literals,
  called names, operator kinds, accessed attribute names). Drifted
  logging-message strings and equality/dunder/`@property` boilerplate are
  handled specially. Built and tuned against an 89-case adversarial corpus
  (`tests/fixtures/duplication_similar/`) with a scorer
  (`benchmarks/score_similar.py`): **precision 1.000 / recall 0.850 /
  F1 0.919**. Enable and tune via `[tool.lanorme.similarity]` (`enabled`,
  `min_statements`, and the per-anchor thresholds).

### Changed

- `DRY-001` documentation now describes it accurately as an **exact structural
  clone** detector (it was loosely called "near-duplicate"); the genuine
  near-duplicate cases are now `SIMILAR-001`.

## [0.6.0]

### Added

- `lanorme check --show-config`: prints the discovered config file (so you can
  see whether a `lanorme.toml` or `[tool.lanorme]` table actually loaded) and
  the effective settings for every registered check, then exits without running
  anything. Opt-in checks are listed with their state (for example
  `restating   enabled=False   (opt-in, not enabled)`), which makes it obvious
  that a default-off check is not silently active. This is the fast way to
  debug a config that loaded empty: the most common cause is the
  `[tool.lanorme.<check>]` (in `pyproject.toml`) versus `[<check>]` (in a
  dedicated `lanorme.toml`) table-prefix difference.

## [0.5.1]

### Changed

- First release published to PyPI: `uv tool install lanorme` (or
  `pipx install lanorme` / `pip install lanorme`). Publishing runs through
  PyPI Trusted Publishing from GitHub Actions on each GitHub Release, so no
  API token is stored.
- The project moved to the `lanorme` GitHub organisation; all project URLs
  now point to `github.com/lanorme/lanorme` (the old paths redirect).

## [0.5.0]

### Added

- `attribute_access` check, opt-in (default-off), advisory warnings:
  - `ATTR-001`: `hasattr(x, "name")` with a literal identifier name (duck
    typing; prefer a `runtime_checkable` Protocol with `isinstance`, or
    EAFP).
  - `ATTR-002`: `getattr(x, "name")` (no default), `setattr(x, "name", v)`,
    or `delattr(x, "name")` with a literal identifier name (use direct
    attribute access `x.name`).
  - High-confidence cases only: three-argument `getattr` with a default,
    dunder names, non-identifier names, and files under `tests/` are exempt.
    Dynamic (non-literal) names are exempt unless `flag_dynamic = true`.
    Enable via `[tool.lanorme.attribute_access] enabled = true`. The default
    was chosen by measuring the rule against the Python standard library,
    where `hasattr` is dominated by legitimate platform/feature detection
    (no Protocol fix), so the check ships off.
- `Configurable` protocol in the public API: a `runtime_checkable` Protocol
  for checks that accept a `[tool.lanorme.<name>]` settings table. The CLI
  now selects configurable checks with `isinstance(check, Configurable)`.

## [0.4.0]

### Added

- Top-level `[tool.lanorme] source_root` key. It decouples the architectural
  root from the scan target for the two layout-aware checks (`layer_deps` and
  `port_coverage`) only. With `source_root = "src/pkg"`, a single
  `lanorme check .` from the repo root classifies layers under
  `src/pkg/domain/`, `src/pkg/api/`, etc., while every other check keeps
  scanning the whole tree. `composition_root`, `ports_dir`, and
  `adapter_roots` are interpreted relative to `source_root`. A scanned file
  that is not under `source_root` is layer-exempt (skipped by `layer_deps` /
  `port_coverage`, never flagged), but is still seen by every other check.
  Reported violation paths stay relative to the scan target, so `--exclude`,
  `[tool.lanorme.per-file-ignores]`, and `# noqa` line up unchanged.
  `source_root` is resolved against the scan target (for the intended
  `lanorme check .` from the repo root these are the same directory).
- `exclude` globs are now honoured at file-discovery time, not only in the
  post-filter. An excluded directory is pruned during the walk, so a large
  excluded subtree (`postman/**`, `docs/generated/**`, ...) is no longer read.
  The CLI still post-filters by the same globs as a safety net.

### Changed

- A built-in set of never-source directories is pruned during every check's
  tree walk regardless of configuration: `.git`, `.venv`, `venv`,
  `node_modules`, `__pycache__`, `dist`, `build`, `.ruff_cache`,
  `.pytest_cache`, `.mypy_cache`. This makes `lanorme check .` fast out of the
  box (it no longer descends into a virtualenv or build tree). This is a
  behaviour change not gated behind a config key: a project that deliberately
  kept first-party `.py` files under one of these directory names would no
  longer have them scanned. The `stray_artifacts` check already pruned the
  same set, so its `JUNK` rules are unaffected.

## [0.3.0]

### Added

- `layer_deps` and `port_coverage` are now configurable via
  `[tool.lanorme.layer_deps]` and `[tool.lanorme.port_coverage]`. All keys
  are optional and the built-in defaults reproduce the previous behaviour.
  - `layer_deps`: `composition_root` (path globs), `layers`, and a nested
    `[tool.lanorme.layer_deps.allowed]` table mapping each layer to the
    layers it may import.
  - `port_coverage`: `ports_dir`, `adapter_roots`, `composition_root`
    (path globs), `skip_files`, `ports_without_impl`.

### Changed

- The composition root is now matched with `fnmatch` globs against the
  source-relative path, in both `layer_deps` (LAYER-005) and
  `port_coverage` (PORT-003), instead of a directory `startswith` /
  substring test. A module **file** such as `api/dependencies.py` can now
  be a composition root; previously only an `api/dependencies/` **directory**
  was recognised. The defaults match the same paths as before, so projects
  that do not set the new keys see no change.
- LAYER-005 rule text changed from "only `api/dependencies/` may import
  from infrastructure" to "only the composition root may import from
  infrastructure" (it is now configurable).
- `port_coverage` now scans each adapter root **recursively** (`rglob`),
  where it previously scanned only the top level of
  `infrastructure/services/`. A project with adapter files in
  subdirectories of an adapter root may now see those files evaluated by
  PORT-001 and contribute to PORT-002 coverage. For a flat
  `infrastructure/services/*.py` layout there is no change. This is the one
  behaviour change not gated behind a config key.

## [0.2.0]

### Changed

- `CMT-001` recall pushed from 0.667 to 1.000 by extending the comment-as-
  code parser with wrapping strategies for the shapes `ast.parse` rejects
  standalone: block headers (`if x:`, `for x in y:`, `def f():`, `class C:`)
  are tried with a `pass` body; `try:` adds a synthetic `except`; `elif` /
  `else` / `except` / `finally` are tried inside their parent block; bare
  `return` / `yield` / `raise` are tried inside a synthetic `def _():`; and
  decorator lines (`@foo`) are tried followed by `def _(): pass`. Also
  added `ast.If` / `ast.Try` / `ast.Match` / `ast.Return` to the code-node
  whitelist. Scored: **F1 = 0.793 -> 0.992** (P = 0.978 -> 0.985,
  R = 0.667 -> 1.000).
- `CMT-005` moved from the `comments` check to a new `restating` check.
  Same rule code, same precision-funnel detector (P = 1.000, R = 0.418,
  F1 = 0.589). Configuration key changed from `[tool.lanorme.comments]
  restating = true` to `[tool.lanorme.restating] enabled = true`.
- `SQL-001` rewritten AST-based: only flags raw SQL that reaches a
  database execution sink (`.execute` / `.executemany` /
  `.executescript` on a DB-shaped receiver, or `read_sql` /
  `read_sql_query`). Unwraps `text(...)` constructors, resolves
  module-level and function-local string constants, treats `+` /
  `%`-formatted / `.format`-built SQL as interpolated, and recognises
  parameterised executes (placeholder + params arg) as safe.
  Scored against the bundled corpus: **F1 = 0.761 -> 1.000**
  (P = 0.686 -> 1.000, R = 0.854 -> 1.000).
- `SECRETPY-001` rewritten AST-based: flags credential-named
  assignments (variable, dict-literal key, call kwarg) plus shape-only
  matches (PEM, JWT, Bearer, DB-URL-with-creds, vendor-prefixed
  tokens for AWS / GitHub / Slack / Stripe). Placeholder markers
  (`<your-...>`, `REPLACE_ME`, `example`, ...) skip a value unless it
  is high-entropy enough (32+ chars, mixed case, digits) to defeat the
  marker. Scored: **F1 = 0.658 -> 1.000** (P = 0.758 -> 1.000,
  R = 0.581 -> 1.000).
- `SECRETPY-001` moved from the `security_patterns` check to a new
  `secrets` check. Rule code unchanged; the check name changed.
  Users running `lanorme check . --check=security_patterns` no longer
  get SECRETPY-001 flags; run `--check=secrets` instead, or rely on
  the default-on full run.

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
