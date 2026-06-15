# LaNorme rule reference

This reference describes every rule code LaNorme can emit, one section per code, covering what each rule catches, what it deliberately ignores, where to configure it, and its measured precision, recall, and F1 where a labelled corpus exists.

One section per rule code emitted by LaNorme. Each section says what the
rule catches, what it does not, where to configure it, and (where the
rule has a labelled corpus under `evals/corpora/` and a scorer under
`evals/`) the measured precision / recall / F1 on that corpus.

Live rule list: `lanorme rules`.
Default policy and per-check configuration: see the README.

The rules are grouped by category in the same order as `lanorme rules`.

---

## Attribute access: `ATTR-001` / `ATTR-002`

Opt-in (default-off); both are advisory warnings. Enable with
`[tool.lanorme.attribute_access] enabled = true`. The premise: when an
attribute name is a constant at the call site, the type is known too, so the
dynamic form only hides the attribute from the type checker.

- `ATTR-001`: `hasattr(x, "name")` with a literal identifier name. Branching
  on structure is duck typing; prefer a `runtime_checkable` `Protocol` with
  `isinstance`, or EAFP (`try: ... except AttributeError`).
- `ATTR-002`: `getattr(x, "name")` (no default), `setattr(x, "name", v)`, or
  `delattr(x, "name")` with a literal identifier name. Use direct attribute
  access (`x.name`).

High-confidence cases only. Exempt: three-argument `getattr(x, "name",
default)` (the safe-access idiom); dunder names (`__class__`, `__name__`, ...);
names that are not valid identifiers (cannot be written as `x.name`); and files
under `tests/`. Dynamic names (`getattr(x, name)`) are reflection and exempt
unless `flag_dynamic` is set.

Config:
```toml
[tool.lanorme.attribute_access]
enabled      = true
flag_dynamic = false   # also flag non-literal (reflective) attribute names
```

---

## Comments: `CMT-*` and `PROSE-*` on .py

### `CMT-001`: No commented-out code

Default-on. Walks every `#` comment and parses its text as Python; if the
result is one of `_CODE_NODES` (imports, assigns, defs, control flow,
returns / raises / asserts, ...), the comment is treated as disabled code.
Guards: comments ending in `.` / `?` / `!` are prose; `foo(...)` (literal
`...`) is illustrative; `label: type` with no value is documentation; tooling
pragmas (`# noqa`, `# type:`, ...) are skipped; and the lines of a
[PEP 723](https://peps.python.org/pep-0723/) `# /// script` ... `# ///` inline
metadata block are tooling, not code.

To recover the shapes `ast.parse` rejects standalone, the comment text is
tried in several wrapping strategies before being declared prose:

- Block headers ending in `:` are tried with a `pass` body.
- `try:` is tried with a `pass` body plus a synthetic `except Exception`.
- `elif` / `else` are tried inside an `if True: pass` prefix.
- `except` / `finally` are tried inside a `try: pass` prefix.
- Bare `return` / `yield` / `raise` are tried inside `def _(): ...`.
- Decorator lines (`@foo`) are tried followed by `def _(): pass`.

Measured against the 165-comment corpus under
`evals/corpora/comments_commented_code/` with `evals/score_cmt001.py`:
**P = 0.985 / R = 1.000 / F1 = 0.992** (TP = 66, FP = 1, FN = 0). The
single FP is an illustrative call signature following a `Typical usage:`
header.

Config:
```toml
[tool.lanorme.comments]
commented_code = true   # default-on; set false to disable CMT-001
```

### `CMT-002`: No verbose comments

Default-on. Flags any single comment longer than `max_comment_chars`
(default 120) and any block of consecutive standalone comments longer
than `max_block_lines` (default 6).

Config:
```toml
[tool.lanorme.comments]
verbose           = true   # default-on; set false to disable CMT-002
max_comment_chars = 120
max_block_lines   = 6
```

### `CMT-005`: No comments that restate the next line of code

Default-off. **Experimental.** Lives in its own `restating` check.
Precision-first by design: it only flags a comment when every content word
and verb maps onto the adjacent statement, and an allowlist exempts comments
that carry a why, a caveat, a unit, or a reference. It will miss synonym
paraphrases. Full design: `docs/cmt005-design.md`.

Measured against the 167-comment corpus under
`evals/corpora/comments_restating/` with `evals/score_cmt005.py`:
**P = 1.000 / R = 0.418 / F1 = 0.589** (TP = 33, FP = 0, FN = 46, TN = 88).
The 0.418 recall is bounded by the design's refusal to chase synonym
paraphrases without losing precision.

Config:
```toml
[tool.lanorme.restating]
enabled = true
```

### `PROSE-001` / `PROSE-003` on comments and docstrings

Off until enabled. The same rule codes that the `prose` check emits on
Markdown also fire here, on `#` comments and `"""..."""` docstrings,
when configured.

Config:
```toml
[tool.lanorme.comments]
em_dash = true   # emit PROSE-001 on comments/docstrings
emoji   = true   # emit PROSE-003 on comments/docstrings
```

---

## Docs: `DOCS-001..008`

Opt-in (default-off), tree-scoped. Enforces a familiar Diataxis-style structure
and accessibility on a Markdown documentation tree. It inspects only Markdown
under `docs_root` (default `docs`); files anywhere else are ignored, so it never
imposes a docs structure on source trees or stray Markdown. Headings and images
inside fenced code blocks are never matched, so a sample showing a hash heading
or an image link is left alone. `DOCS-001..004` are build-failing errors;
`DOCS-005..008` are advisory warnings.

- `DOCS-001`: a content page has exactly one level-1 heading.
- `DOCS-002`: heading levels descend one step at a time (no skipped levels).
- `DOCS-003`: a content page opens with a canonical skimmer line. The first
  prose line after the H1 must begin with one of `This page`, `This tutorial`,
  `This guide`, `This reference`, `This how-to`, or `This explanation`.
- `DOCS-004`: every image carries non-empty alternative text, for both
  Markdown image links and HTML `img` tags.
- `DOCS-005`: prefer SVG or Mermaid over a local raster image (warning).
- `DOCS-006`: a known section directory that has pages carries an `index.md`
  landing page (warning).
- `DOCS-007`: every page lives in a known section or is a known top-level
  page (warning).
- `DOCS-008`: headings are not numbered by hand; renderers number sections
  for you (warning).

Vendored or generated directories (`.git`, `.venv`, `node_modules`,
`__pycache__`, `dist`, `build`, and so on) are never treated as part of a docs
tree.

Config (all keys optional; the defaults are shown):
```toml
[tool.lanorme.docs]
enabled   = true                  # default false (the whole check is opt-in)
docs_root = "docs"                # tree to inspect, relative to the scan target
# Diataxis section directories expected under docs_root.
sections  = ["tutorials", "how-to", "reference", "explanation"]
# Pages allowed at the top level without a section home (DOCS-007).
known_top_level = [
  "index.md",
  "RULES.md",
  "reference/configuration.md",
  "reference/rules-index.md",
  "reference/cli.md",
]
# Image extensions treated as raster formats for DOCS-005.
raster_extensions = ["png", "jpg", "jpeg", "gif", "webp", "bmp"]
allow = ["**/logo.png"]           # globs exempt from the prefer-SVG warning (default empty)
```

The check is tree-scoped (`scope = "tree"`): it reads the directory layout, not
only individual files, so the section-index and quadrant rules can reason about
where each page sits.

---

## Domain terminology: `TERM-NNN`

Configurable ubiquitous-language enforcement. Inert by default. Each
rule the user configures gets a code from the `TERM-` family.

Config:
```toml
[[tool.lanorme.domain_terms.rules]]
id        = "TERM-001"
canonical = "Account"
forbidden = ["Acct", "Acnt"]

[[tool.lanorme.domain_terms.rules]]
id        = "TERM-002"
canonical = "Customer"
forbidden = ["Cust", "Client"]
```

---

## Duplication: `DRY-001`

Default-on. Detects **exact structural clones**: functions with an identical
normalised AST body and at least five statements. Normalisation strips variable
names and string literals, so two functions differing only in identifier
spelling or string-constant content still match. It is precise but strict: a
single added statement, a reordering, a changed number, or a renamed attribute
defeats the match. For the fuzzier "these should share a helper" cases, see
`SIMILAR-001` below.

Config: none. False positives on intentionally parallel
adapters across bounded contexts are a known limit; suppress them with
`[tool.lanorme.per-file-ignores]` or `# noqa: DRY-001`.

---

## Near-duplicate: `SIMILAR-001`

Opt-in (default-off), advisory **warning** (never fails the build). The fuzzy
companion to `DRY-001`: it catches near-duplicates that the exact check misses
(one or two added statements, reordering, a changed number, a renamed
attribute, a renamed call) so a reviewer can decide whether to extract a shared
helper.

Two functions in a file are compared on two signals. **Structure**: a token
sequence over the body that abstracts away variable names, attribute names and
numbers, scored with `difflib` (so a one-statement or reorder drift still
aligns). **Anchors**: the meaning-bearing tokens `DRY-001` discards: string
literals, called names, operator kinds, and accessed attribute names, each
scored by weighted Jaccard. A pair flags only when the structure is similar
**and** every anchor agrees, which keeps precision high: parallel boilerplate
that shares a shape but differs in its string keys or source attributes (config
builders, dispatch tables, field mappers, framework handlers) is rejected.
Equality/dunder/`@property` boilerplate and drifted logging-message strings are
handled specially. Measured on the bundled corpus
(`evals/corpora/duplication_similar/`, scorer `evals/score_similar.py`):
**precision 1.000 / recall 0.850 / F1 0.919**. Known recall gaps: fully renamed
attribute sets and error-message-only drift.

```toml
[tool.lanorme.similarity]
enabled = true
# threshold overrides (defaults shown):
min_statements = 5
struct_ratio   = 0.55
str_jaccard    = 0.60
op_jaccard     = 0.60
call_jaccard   = 0.35
attr_jaccard   = 0.10
```

---

## File limits: `SIZE-*` / `COMPLEXITY-001` / `PARAM-001`

All default-on.

- `SIZE-001`: Python files. Warn at 300 effective (non-blank,
  non-comment) lines; error at 500.
- `SIZE-002`: functions and methods. Warn at 50 lines; error at 80.
- `SIZE-003`: classes with more than 10 methods (warning only). Useful
  as a smell on services and views; on rich aggregate roots in a DDD
  codebase, expect to silence it via `per-file-ignores`.
- `COMPLEXITY-001`: cyclomatic complexity. Warn at 10; error at 15.
  Mirrors the ruff `C901` / `mccabe` defaults.
- `PARAM-001`: function/method parameter count, excluding `self` /
  `cls`. Warn at 5; error at 8.

Skips `__init__.py`, `conftest.py`, `alembic/`, `migrations/`, and
`test_*` files.

---

## Forbidden paths: `PATH-001`

Inert until configured.

Config:
```toml
[tool.lanorme.forbidden_paths]
dirs = ["legacy_src", "build_artifacts"]
```

---

## Layer dependencies: `LAYER-001..006`

For hexagonal / layered codebases with a `domain/`, `application/`,
`infrastructure/`, `api/` layout. Inert in their absence.

If the layers live under a nested package directory, set the top-level
`[tool.lanorme] source_root` (e.g. `"src/myproject"`) so they are classified
relative to it. Files outside `source_root` are layer-exempt;
`composition_root` is then read relative to `source_root` too. Reported paths
stay relative to the scan target.

- `LAYER-001`: `domain/` must not import any other layer.
- `LAYER-002`: `application/` may only import from `domain/`.
- `LAYER-003`: `infrastructure/` may only import from `domain/` and
  `application/`.
- `LAYER-004`: `api/` may only import from `domain/` and
  `application/`.
- `LAYER-005`: only the composition root may import from
  `infrastructure/`.
- `LAYER-006`: a `transport_layers` entry is not among the configured
  `layers`, so it has no effect (advisory **warning**, exit 0).

These rules track Cockburn's hexagonal architecture and Seemann's
composition-root pattern.

The composition-root exception applies to any layer listed in
`transport_layers` (default `["api"]`). Apps with several peer transport
adapters (a REST `api/`, an `mcp_server/`, a `grpc_server/`) can list them all
so each keeps its own composition root. A transport peer must also appear in
`layers` and be given an `allowed` entry.

Config (all keys optional; the defaults are shown):

```toml
[tool.lanorme.layer_deps]
# Files allowed to import infrastructure (the composition root).
# fnmatch globs against the source-relative path, so a module FILE
# (api/dependencies.py) is recognised, not only a directory.
composition_root = ["api/dependencies/**", "api/v1/dependencies/**", "api/v1/main.py"]

# For layouts whose layers differ. Defaults shown.
layers = ["domain", "application", "infrastructure", "api"]

# Transport (inbound adapter) layers eligible for the composition-root
# exception. A peer must also appear in layers and get an allowed entry.
transport_layers = ["api"]
[tool.lanorme.layer_deps.allowed]
application    = ["domain"]
infrastructure = ["domain", "application"]
api            = ["domain", "application"]
```

---

## Meta: `META-001..005`

Self-validation that every registered check produces well-formed output.

- `META-001`: non-empty `name`.
- `META-002`: non-empty `description`.
- `META-003`: non-empty `rules` list.
- `META-004`: `CheckResult.check` matches the check's `name`.
- `META-005`: violations carry a non-empty `file`, `rule`, `message`,
  and `fix`.

If you ship a plugin, run `lanorme check . --check=meta` once to confirm
it conforms.

---

## Keyword arguments: `KWARG-001`

Opt-in. With `enabled = true`, every multi-argument function definition
must contain a bare `*` separator to force keyword-only call sites.

Config:
```toml
[tool.lanorme.named_args]
enabled = true
```

---

## Naming conventions: `NAMING-001..004`

- `NAMING-001`: opt-in. Repository methods (files under
  `infrastructure/repositories/` or `infrastructure/persistence/`) that use
  a non-canonical synonym prefix (`fetch_` / `retrieve_` / `find_` /
  `remove_` / `add_`) are flagged and steered to the CRUD equivalent
  (`get_` / `create_` / `update_` / `delete_` / `list_`). Conflicts with the
  DDD ubiquitous-language convention; off by default.
- `NAMING-002`: opt-in. Service methods (files under `application/services/`)
  that use the same synonym prefixes are flagged and steered to the CRUD
  equivalent. Conflicts with domain-named operations (`approve_loan`,
  `transfer_funds`); off by default.
- `NAMING-003`: default-on warning. Endpoint handler names (in files
  under `api/v1/endpoints/`) should match their HTTP verb (`get_user` on
  `@router.get`, `delete_user` on `@router.delete`). Health probes and
  auth-issuance handlers are exempt.
- `NAMING-004`: default-on warning. Functions whose return annotation
  is `bool` should use a boolean prefix (`is_` / `has_` / `can_` /
  `should_`).

Config:
```toml
[tool.lanorme.naming_consistency]
repo_crud    = true   # enable NAMING-001
service_crud = true   # enable NAMING-002
```

---

## Pattern divergence: `IMPORT-001` / `ENDPOINT-001`

- `IMPORT-001`: default-on. Imports must live at the top of the module
  (`import` / `from x import y` statements must not be nested inside a
  function or method body). Equivalent to ruff `PLC0415` with a different
  default. Imports inside an `if TYPE_CHECKING:` guard are exempt, as are
  files under `infrastructure/observability/` and `api/v1/main.py`
  (conditional startup wiring); `test_*` files are skipped.
- `ENDPOINT-001`: default-on warning. Functions defined in files under
  `api/v1/endpoints/` must not exceed nesting depth 4. Deep endpoints
  correlate with missed branches in auth and validation paths.

---

## Port coverage: `PORT-001..003`

For hexagonal codebases with `application/ports/`. As with `layer_deps`, the
top-level `[tool.lanorme] source_root` anchors `ports_dir`, `adapter_roots`,
and `composition_root` under a nested package directory when set.

- `PORT-001`: every adapter file (under the adapter roots) must import
  from the ports directory.
- `PORT-002`: every `Protocol` declared in the ports directory must
  have at least one implementation. Treat as advisory: ports realised
  only by test doubles or sibling plugins are legitimate.
- `PORT-003`: no direct import or instantiation of an infrastructure
  adapter from the `api/` layer outside the composition root.

Config (all keys optional; the defaults are shown):

```toml
[tool.lanorme.port_coverage]
ports_dir        = "application/ports"     # where port Protocols live
adapter_roots    = ["infrastructure/services"]  # dirs scanned for adapters (recursive)
composition_root = ["*dependencies/*", "*v1/main.py"]  # PORT-003 exemption (globs)
skip_files         = ["__init__.py"]
ports_without_impl = ["repositories.py", "unit_of_work.py", "otel.py", "metrics.py"]
```

Adapter roots are scanned recursively, so widening `adapter_roots` to
`["infrastructure"]` picks up adapters in per-integration subdirectories.

---

## Prose: `PROSE-001..004` on Markdown

Off until enabled.

- `PROSE-001`: em dashes (`-`) in prose.
- `PROSE-002`: American spellings; suggests the British form.
- `PROSE-003`: emoji in prose.

Skips fenced code blocks (` ``` `, `~~~`) and inline `` `code` `` spans.

### `PROSE-004`: Em-dash density above natural English

Advisory warning, opt-in (default-off). Where `PROSE-001` bans every em dash
outright, `PROSE-004` instead measures how often em dashes appear and warns once
per file when the density runs above what natural English sustains. It reuses
the same code-span and fenced-block stripping as the other prose rules, so it
measures the remaining prose alone.

The heuristic has an eligibility floor and two fire thresholds. A file is only
measured when it clears all three floor values (`min_em` em dashes, `min_words`
words, `min_sentences` sentences), which keeps the rule silent on anything too
short to judge. It then fires only when **both** density thresholds are
exceeded: em dashes per 1000 words above `em_per_1000` **and** the fraction of
sentences carrying an em dash above `em_sentence_fraction`. ANDing the two axes
stops a single high reading from tripping the warning. Setting `em_dash = false`
while `em_dash_density = true` switches a region from the `PROSE-001` ban to
this density advisory.

Measured on the labelled corpus `evals/corpora/prose_em_dash` (run
`evals/score_prose004.py`): **P = 1.000 / R = 1.000 / F1 = 1.000** (TP = 3,
FP = 0, FN = 0, TN = 11). The corpus exists to prove the calibrated thresholds
do not false-positive on natural prose.

Config:
```toml
[tool.lanorme.prose]
enabled         = true
extensions      = [".md", ".markdown"]   # default
em_dash         = true                   # default; PROSE-001 ban
emoji           = true                   # default
em_dash_density = true                   # enable PROSE-004 (default false)

[tool.lanorme.prose.spellings]
customize = "customise"             # extend or override the built-in US->UK map

[tool.lanorme.prose.density]
min_em               = 4      # eligibility floor: minimum em dashes
min_words            = 400    # eligibility floor: minimum words
min_sentences        = 30     # eligibility floor: minimum sentences
em_per_1000          = 30.0   # fire threshold: em dashes per 1000 words
em_sentence_fraction = 0.50   # fire threshold: fraction of sentences with an em dash
```

---

## Security calls: `SHELL-001` / `DESERIAL-001` / `EVAL-001` / `CRYPTO-001` / `TLS-001` / `DEBUG-001`

All default-on. Single AST walk. Precision-first: when the AST shape is
ambiguous, the rule prefers a false negative over a false positive (no
false sense of security). Use `# noqa: <CODE>` for legitimate uses (e.g.
a pickle load on a trusted local cache) or `[tool.lanorme.per-file-ignores]`
for broader patches.

- `SHELL-001`: `subprocess.run` / `call` / `check_call` /
  `check_output` / `Popen` with `shell=True`; `os.system`; `os.popen`.
- `DESERIAL-001`: `pickle.load(s)`, `marshal.load(s)`, `dill.load(s)`,
  `cPickle.load(s)`, `yaml.load` without `Loader=SafeLoader` /
  `CSafeLoader` / `BaseLoader`, `yaml.unsafe_load`.
- `EVAL-001`: `eval` / `exec` / `compile` where the first argument is
  not a string literal. (Literal-arg `compile(...)` flows are accepted.)
- `CRYPTO-001`: `hashlib.md5` / `hashlib.sha1` used for security
  (`usedforsecurity=False` is honoured), `hashlib.new("md5"/"sha1", ...)`,
  `ssl.PROTOCOL_SSLv2` / `SSLv3` / `TLSv1` / `TLSv1_1`.
- `TLS-001`: `requests` / `httpx` / `aiohttp` call with `verify=False`,
  `ssl._create_unverified_context`, `ssl.CERT_NONE` attribute reference.
- `DEBUG-001`: `Flask(...)` / `FastAPI(...)` constructor with
  `debug=True`, `*.run(debug=True)` / `*.run_server(debug=True)`,
  module-level `DEBUG = True` in `*settings.py` / `*config.py`.

Each rule has a positive + negative unit test under
`tests/unit/test_security_calls.py` locking the AST shape.

---

## Security patterns: `AUTHN-001` / `SQL-001` / `SECRETPY-001`

- `AUTHN-001`: default-on. `@router.post` / `put` / `patch` / `delete`
  handlers must have an auth dependency (a parameter annotated with
  `Depends(get_current_user)` or `Depends(require_*)`). FastAPI-shaped;
  the rule checks for **authentication presence only**, not
  authorisation. Only endpoint files under `api/` are scanned. Exempt
  endpoints: `login`, `logout`, `refresh`, `token`.
- `SQL-001`: default-on. AST-based: only flags SQL string literals that
  reach a database execution sink (`.execute` / `.executemany` /
  `.executescript` on a DB-shaped receiver, or `read_sql` /
  `read_sql_query`). Unwraps `text(...)` constructors, resolves module-
  level and function-local string constants, and treats `+` /
  `%`-formatted / `.format`-built SQL as interpolated (always flagged).
  Static SQL passed alongside a `params=` / `parameters=` kwarg (or a
  second positional on `.execute`) with placeholder marks (`:name`,
  `%s`, `?`) is treated as safely parameterised and not flagged.
  Excludes `alembic/` and `test_*` files. Measured against
  `evals/corpora/security_raw_sql/` (120 labels): **P = 1.000 /
  R = 1.000 / F1 = 1.000**. Known limitations not in the corpus: SQL
  built across multiple statements with helper functions; lazy-loaded
  query templates; non-Python query files.
- `SECRETPY-001`: default-on. Lives in the `secrets` check. AST-based:
  flags credential-named assignments
  (variable, dict key, or call kwarg) whose value looks like a real
  secret, plus shape-only matches (PEM private-key blocks, JWT-shaped
  tokens, Bearer headers, DB / cache URLs with embedded `user:pass@host`
  credentials, and vendor-prefixed credentials: AWS `AKIA` / `ASIA`,
  GitHub `ghp_` / `gho_` / `github_pat_`, Slack `xox*`, Stripe
  `sk_live_` / `sk_test_`). Names whose first segment is `help_` /
  `hint_` / `msg_` / etc. are documentation; names whose last segment
  is structural (`pattern`, `endpoint`, `header`, `name`, `len`, ...)
  are not credentials. Placeholder markers (`<your-...>`, `REPLACE_ME`,
  `example`, ...) skip a value unless it is high-entropy enough (32+
  chars, mixed case, digits) to defeat the marker (AWS docs-style
  example secret keys). Excludes `conftest.py`, `seed_dev.py`, and
  files starting with `test_`. Measured against
  `evals/corpora/security_hardcoded_secrets/` (155 labels):
  **P = 1.000 / R = 1.000 / F1 = 1.000**. **Scope warning**:
  Python-source only; `.env`, `*.yaml`, `*.ipynb`, `*.tf`, `Dockerfile`,
  GitHub Actions workflows are out of scope until a separate
  non-Python rule lands.

---

## Skills: `SKILL-001..006`

On by default. Validates files named `SKILL.md` against the [Agent Skills
specification](https://agentskills.io/specification). It only fires where a
`SKILL.md` exists, so it is silent on projects without skills. The frontmatter
parser is stdlib only and never turns its own uncertainty into a failure: if a
required value cannot be read cleanly it warns `SKILL-006` rather than reporting
the value as missing.

Build failing:

- `SKILL-001`: `name` is required; 1 to 64 characters; lowercase `a-z`, digits
  and hyphens only; no leading, trailing or consecutive hyphen; and it must match
  the parent directory name.
- `SKILL-002`: `description` is required, non-empty, and at most 1024 characters.
- `SKILL-003`: optional fields are well formed: `compatibility` at most 500
  characters, `metadata` a map of string keys to string values, and
  `allowed-tools` a single string.

Advisory warnings:

- `SKILL-004`: the `SKILL.md` body stays under 500 lines (progressive disclosure).
- `SKILL-005`: relative Markdown links resolve to a file that exists. Links in
  fenced code blocks, external URLs, and `#anchors` are ignored.
- `SKILL-006`: the frontmatter is present but could not be parsed with confidence.

Config:
```toml
[tool.lanorme.skills]
enabled     = true   # default
check_links = true   # default; set false to skip SKILL-005
```

---

## Stale paths: `STALE-001`

Inert until configured. Flags references to old path tokens in
docstrings and comments after a refactor.

Config:
```toml
[tool.lanorme.stale_paths]
tokens = ["src/", "old_pkg/"]
```

---

## Stray artifacts: `JUNK-001/002`

Default-on. Surface tree clutter, including the privacy-relevant cases
of screenshots and editor backups that frequently contain secrets or
PII.

- `JUNK-001`: files matching scratch / temp / OS / build name globs such
  as `screenshot*`, `scratch*`, `untitled*`, `*~`, `*.bak`, `*.orig`,
  `*.rej`, `*.swp`, `*.swo`, `*.tmp`, `tmp.*`, `temp.*`, `.DS_Store`,
  `Thumbs.db`, `desktop.ini`, `nohup.out`, `core.*`, `*.pyc`, `*.pyo`,
  `.coverage`, `coverage.xml`.
- `JUNK-002`: image / binary extensions outside an asset directory.
  Default extensions: `.png`, `.jpg`, `.jpeg`, `.gif`, `.bmp`, `.webp`.
  Default asset directories: `assets/`, `static/`, `images/`, `img/`,
  `media/`, `public/`, `docs/`, `.github/`.

Config:
```toml
[tool.lanorme.stray_artifacts]
patterns   = ["*.heic"]            # extra name globs flagged as JUNK-001
extensions = [".zip", ".pdf"]      # extra extensions flagged as JUNK-002
assets     = ["screenshots"]       # extra dirs where binaries are allowed
allow      = ["docs/diagram.png"]  # never flag these (globs)
exclude    = ["sandbox"]           # extra directories to skip entirely
```

---

## Strong types: `TYPE-001..004`

Default-on. Skips files under `tests/` and `migrations/`. `TYPE-001..003` are
build-failing; `TYPE-004` is an advisory warning.

- `TYPE-001`: `dict[str, Any]` (and other weakly-typed dict containers)
  in function signatures or return annotations. Pushes toward DTOs,
  TypedDicts, and value objects.
- `TYPE-002`: bare `dict` / `list` / `tuple` / `set` without type
  parameters.
- `TYPE-003`: `**kwargs` must be annotated with a concrete type or
  `Unpack[TypedDict]`; bare `**kwargs: Any` is rejected.
- `TYPE-004` (advisory warning): a function with at least one annotated
  parameter that returns a real value in its own scope should also declare a
  return type. This is the high-signal completeness subset of ruff's `ANN`,
  not blanket presence enforcement: it fires only when the parameters are
  already typed and a value escapes, so a fully untyped function or a procedure
  that returns nothing is left alone. Generators (own-scope `yield`) are exempt;
  returns inside a nested `def` or `lambda` do not count.

---

## Test coverage: `TESTFILE-001`

Default-on warning. For each Python file under one of the hardwired
production directories, verify that a matching `test_*.py` partner (by name
or by import reference) exists under `tests/integration/`. Note this is
**file presence**, not coverage; it cannot tell you whether the test
actually exercises the module.

Config: none. The scanned production directories (`api/v1/endpoints`,
`application/services`, `application/commands`, `application/queries`,
`infrastructure/repositories`, `infrastructure/signing`,
`infrastructure/secrets`) and the exempt modules (`dependencies`, `main`,
`logging`, `session`) are hardwired.

---

## Test style: `AAA-001` / `AAA-002`

Off until enabled.

- `AAA-001`: test functions with more than `min_statements` (default 3)
  body statements must carry at least `required_markers` (default 2) of
  the AAA section comment markers (`# Arrange`, `# Act`, `# Assert`) or
  their BDD synonyms (`# Given`, `# When`, `# Then`). Setup, exercise,
  call, expect, verify are recognised as additional aliases.
- `AAA-002`: two or more test functions in the same file may not share
  the same `dry_prefix_statements` (default 3) opening statements (the
  arrange block). Extract the shared setup into a pytest fixture or a
  helper.

Config:
```toml
[tool.lanorme.test_style]
enabled               = true
min_statements        = 3
required_markers      = 2     # 1..3
dry_prefix_statements = 3
synonyms              = ["setup", "given", "when", "then"]
```
