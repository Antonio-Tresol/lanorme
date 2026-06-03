# LaNorme

[![PyPI](https://img.shields.io/pypi/v/lanorme.svg)](https://pypi.org/project/lanorme/)
[![Python](https://img.shields.io/pypi/pyversions/lanorme.svg)](https://pypi.org/project/lanorme/)
[![CI](https://github.com/lanorme/lanorme/actions/workflows/ci.yml/badge.svg)](https://github.com/lanorme/lanorme/actions/workflows/ci.yml)
[![Licence: MIT](https://img.shields.io/badge/licence-MIT-blue.svg)](LICENSE)

LaNorme makes a codebase's standard executable. It automates the mechanical side
of code review: on every commit it checks cyclomatic complexity, file and
function size, duplication, stale doc references, architectural boundaries, and
naming conventions, and fails the build when they drift.

The built-in _normes_ cover the common ground. A plugin interface lets a team
encode its own, so the standard you agree on is the standard the build keeps. The
same gate runs in CI and inside an AI agent's loop, so people and agents write to
one bar and the codebase stays clean as it grows.

Standard library only. No runtime dependencies. Python 3.13+.

## Why LaNorme

- **Keep a growing codebase clean.** Complexity, size, duplication, and stale
  docs are caught the moment they appear, while the fix is still small.
- **Enforce architecture and conventions.** Layering, ports-and-adapters wiring,
  and your own domain vocabulary become checks any contributor can run.
- **Gate AI-generated code.** Hand an agent the same _normes_ your team codes to:
  it gets concrete, mechanical feedback on what good looks like here, and
  non-compliant output fails before it reaches a human.
- **Spend review on judgement.** Reviewers focus on design and correctness
  because the mechanical checks are already green.

## Install

From PyPI:

```console
uv tool install lanorme       # or: pipx install lanorme, pip install lanorme
```

Run it once without installing anything:

```console
uvx lanorme check .
```

Or install straight from source:

```console
uv tool install "git+https://github.com/lanorme/lanorme@v0.8.0"
```

Releases are tagged `vX.Y.Z`; see the [releases page](https://github.com/lanorme/lanorme/releases) for notes.

## Usage

```console
lanorme check [PATHS...]              # run every enabled check (default path: .)
lanorme check src/ app/main.py        # any mix of directories and single files
lanorme check . --check secrets       # run one check by name
lanorme check . --check DRY-001       # by rule code or category; runs the check that owns it
lanorme check . --select TYPE,AUTHN   # only these rule codes or categories
lanorme check . --ignore NAMING-003   # skip specific rules
lanorme check . --exclude 'tests/*'   # skip path globs (comma-separated)
lanorme check . --output-format ndjson  # one finding per line, for jq / grep
lanorme check . --output-format json    # one JSON object per check (--json is a shortcut)
lanorme check . --output-format full    # show passing checks too, not just findings
lanorme check . --plugin my_pkg.rules # load a plugin module that registers checks
lanorme check . --show-config         # print discovered config + effective settings
lanorme rules                         # list every registered rule
lanorme rule  SQL-001                 # show the reference for one rule
```

Exit code is `1` when any check fails, `0` when the tree is clean.

By default a run reports only the checks that found something, then a summary line:

```console
$ lanorme check src/
[FAIL] secrets
  VIOLATION: app.py:8 — Hardcoded credential value bound to 'API_KEY'
    Rule: SECRETPY-001: No hardcoded secrets in source code
    Fix: Read the value from an environment variable, secrets manager, or settings module
--- secrets: 1 violations, 0 warnings ---

Summary: 24 checks — 23 passed, 0 warnings, 1 failed.
```

For machine consumption, `--output-format ndjson` prints one JSON object per
finding, which pipes straight into `jq`, `grep`, or `wc -l`:

```console
$ lanorme check src/ --output-format ndjson | jq -c '{code, file, line}'
{"code":"SECRETPY-001","file":"app.py","line":8}
```

### Suppressing a finding

A `# noqa` at the end of a line silences every rule on that line; `# noqa: CODE`
silences only the listed codes (a full code like `SQL-001` or a category like
`SQL`):

```python
def legacy_handler(req):  # noqa: KWARG-001
    return req.text  # noqa
```

For whole directories, use the per-file table in your config (below).

## Configuration

LaNorme walks up from the target path looking for config: a dedicated
`lanorme.toml`, otherwise a `[tool.lanorme]` table in `pyproject.toml`. Command
line flags win over both.

```toml
[tool.lanorme]
select = ["ALL"]                            # rule codes or categories to run
ignore = ["NAMING-003"]                     # rule codes or categories to skip
exclude = ["postman/**", "vendor/*"]        # path globs, pruned at walk time
source_root = "src/myproject"               # architectural root for layer_deps/port_coverage
plugins = ["myproject.checks.house_rules"]  # extra check modules to load

# Silence specific rules for matching paths (the file is still scanned).
[tool.lanorme.per-file-ignores]
"tests/**/*.py"   = ["AAA", "SECRETPY"]
"alembic/**/*.py" = ["SQL"]
"notebooks/*.py"  = ["KWARG", "DRY"]

# Each per-check table is handed to that check.
[tool.lanorme.stray_artifacts]
extensions = [".zip", ".pdf"]               # also flag these (JUNK-002)
allow = ["docs/diagram.png"]                # never flag these (globs)

[tool.lanorme.forbidden_paths]
dirs = ["legacy_src", "build_artifacts"]    # these directories must not exist

[[tool.lanorme.domain_terms.rules]]
id = "TERM-001"
canonical = "Account"
forbidden = ["Acct", "Acnt"]
```

`exclude` globs are pruned during the walk, not just filtered from output, so a
large excluded subtree is never read. A built-in set of never-source
directories (`.git`, `.venv`, `venv`, `node_modules`, `__pycache__`, `dist`,
`build`, `.ruff_cache`, `.pytest_cache`, `.mypy_cache`) is always pruned, so
`lanorme check .` is fast out of the box.

`source_root` applies only to the two layout-aware checks (`layer_deps`,
`port_coverage`). It lets you run `lanorme check .` from the repo root while the
hexagonal layers live under a nested package: layers are classified relative to
`source_root`, files outside it are layer-exempt, and `composition_root` /
`ports_dir` / `adapter_roots` are read relative to it. Every other check still
scans the whole tree.

## What it checks

`lanorme rules` prints the live list. [`docs/RULES.md`](docs/RULES.md) documents
every rule: what it catches and what it does not, its config, and its precision
and recall on the bundled test corpora where those are measured.

On by default, on any project, no config needed:

| Rule | Catches |
|---|---|
| `CMT-001/002` | commented-out code, over-long comment blocks |
| `DRY-001` | near-duplicate function bodies |
| `SIZE-001..003` / `COMPLEXITY-001` / `PARAM-001` | file, function and class size; cyclomatic complexity; parameter count |
| `IMPORT-001` / `ENDPOINT-001` | imports inside function bodies; deeply nested endpoints |
| `NAMING-003/004` | HTTP-verb-to-handler match; boolean-prefix predicates |
| `TYPE-001..003` | `dict[str, Any]`, bare containers, untyped `**kwargs` |
| `AUTHN-001` / `SQL-001` / `SECRETPY-001` | mutation endpoints without an auth dependency; raw SQL at a database call; hardcoded secrets in `.py` |
| `SHELL-001` / `DESERIAL-001` / `EVAL-001` / `CRYPTO-001` / `TLS-001` / `DEBUG-001` | shell injection, unsafe deserialisation, `eval`/`exec`, weak hashes, disabled TLS, debug mode |
| `JUNK-001/002` | screenshots, scratch files, OS junk, stray binaries |
| `TESTFILE-001` | a production module with no `test_*.py` partner |
| `META-001..005` | the checks themselves emit well-formed output |
| `SKILL-001..006` | Agent Skill (`SKILL.md`) frontmatter, naming and link compliance |

Off until you turn them on:

| Rule | Why |
|---|---|
| `LAYER-001..005` | needs a layered layout (`domain/ application/ infrastructure/ api/`) |
| `PORT-001..003` | needs an `application/ports/` directory |
| `TERM-NNN` | needs a vocabulary in `[tool.lanorme.domain_terms]` |
| `PATH-001` / `STALE-001` | need forbidden dirs / stale tokens configured |
| `KWARG-001` | keyword-only call sites; a strong house style |
| `NAMING-001/002` | CRUD method prefixes; conflicts with domain naming |
| `AAA-001/002` | Arrange-Act-Assert markers and DRY in tests |
| `CMT-005` | restating-comment detector; experimental, precision-first |
| `SIMILAR-001` | fuzzy near-duplicate functions (the companion to the exact `DRY-001`) |
| `ATTR-001/002` | `hasattr`/`getattr`/`setattr` with a literal attribute name; a missing-type smell |
| `PROSE-001..003` | em dashes, US spelling and emoji in Markdown or comments |

## Writing a check

A check is any object with `name`, `description`, `rules`, and a `run` method:

```python
from lanorme import CheckResult, Status, Violation, register


class MyCheck:
    name = "my_check"
    description = "What it enforces"
    rules = ["MYCODE-001: the rule, in one line"]

    def run(self, *, src_root: str) -> CheckResult:
        violations: list[Violation] = []
        # inspect files under src_root
        status = Status.FAIL if violations else Status.PASS
        return CheckResult(check=self.name, status=status, violations=violations)


register(MyCheck())
```

Drop it in `lanorme/checks/`, ship it under the `lanorme.checks` entry-point
group, or point at it with `[tool.lanorme] plugins = [...]`. LaNorme finds it
and runs it. See [`CONTRIBUTING.md`](CONTRIBUTING.md) for the setup, the gates,
and the conventions for a new rule.

## Versioning

The public surface is the rule codes you put in `select` / `ignore` /
`per-file-ignores` and the config keys under `[tool.lanorme]`. The question that
decides a version bump is whether a green codebase could go red on upgrade.

- **Patch (`0.y.z`)** keeps every existing codebase's result unchanged: bug
  fixes, docs, internal changes, and opt-in (default-off) checks or new config
  keys with safe defaults.
- **Minor (`0.y.0`)** can newly fail a previously-passing codebase: a new
  default-on check, an existing default-on rule made stricter, a renamed or
  removed rule code, or a changed default. Before 1.0, every breaking change
  lands here.
- **Major (`1.0.0`)** is the stability commitment. After it, a breaking change
  bumps the major.

Every change is listed in [`CHANGELOG.md`](CHANGELOG.md).

## Licence

MIT. See [`LICENSE`](LICENSE).
