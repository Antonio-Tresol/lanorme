# LaNorme

[![PyPI](https://img.shields.io/pypi/v/lanorme.svg)](https://pypi.org/project/lanorme/)
[![Python](https://img.shields.io/pypi/pyversions/lanorme.svg)](https://pypi.org/project/lanorme/)
[![CI](https://github.com/lanorme/lanorme/actions/workflows/ci.yml/badge.svg)](https://github.com/lanorme/lanorme/actions/workflows/ci.yml)
[![Docs](https://img.shields.io/badge/docs-lanorme.github.io-blue.svg)](https://lanorme.github.io/lanorme/)
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

**Full documentation: [lanorme.github.io/lanorme](https://lanorme.github.io/lanorme/).**
Tutorials, how-to guides, the complete rule and configuration reference, and
agent-friendly Markdown: every page is also served raw at its `.md` URL, with an
`llms.txt` index for agents.

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

```console
uv tool install lanorme       # or: pipx install lanorme, pip install lanorme
uvx lanorme check .           # or run once without installing
```

Releases are tagged `vX.Y.Z`; see the [releases page](https://github.com/lanorme/lanorme/releases)
for notes and the [documentation](https://lanorme.github.io/lanorme/) for other
install methods.

## Quickstart

```console
lanorme check [PATHS...]               # run every enabled check (default path: .)
lanorme check . --check secrets        # run one check by name, rule code, or category
lanorme check . --select TYPE,AUTHN    # only these rule codes or categories
lanorme check . --output-format ndjson # one finding per line, for jq / grep
lanorme rules                          # list every registered rule
```

Exit code is `1` when any check fails, `0` when the tree is clean. By default a
run reports only the checks that found something, then a summary line:

```console
$ lanorme check src/
[FAIL] secrets
  VIOLATION: app.py:8 — Hardcoded credential value bound to 'API_KEY'
    Rule: SECRETPY-001: No hardcoded secrets in source code
    Fix: Read the value from an environment variable, secrets manager, or settings module
--- secrets: 1 violations, 0 warnings ---

Summary: 24 checks — 23 passed, 0 warnings, 1 failed.
```

The full command and flag reference, output formats, and `# noqa` suppression are
in the [CLI reference](https://lanorme.github.io/lanorme/latest/reference/cli/).

## What it checks

`lanorme rules` prints the live list. The
[rule reference](https://lanorme.github.io/lanorme/latest/RULES/) documents every rule: what it
catches and what it does not, its config, and its measured precision and recall on
the bundled corpora.

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

Off until you turn them on (layered or hexagonal architecture, domain
vocabulary, house styles, Markdown docs structure, and experimental
precision-first detectors): `LAYER`, `PORT`, `TERM`, `KWARG`, `NAMING-001/002`,
`AAA`, `CMT-005`, `SIMILAR`, `ATTR`, `PROSE`, `DOCS`, `PATH`, `STALE`. The
[rule reference](https://lanorme.github.io/lanorme/latest/RULES/) documents each.

## Configuration

LaNorme walks up from the target path looking for config: a dedicated
`lanorme.toml`, otherwise a `[tool.lanorme]` table in `pyproject.toml`. Command
line flags win over both.

```toml
[tool.lanorme]
extends = ["strict", "hexagonal"]   # adopt bundled profiles; local keys win
select = ["ALL"]
ignore = ["NAMING-003"]
promote = ["TYPE-004"]              # advisory warnings become build-failing errors
exclude = ["postman/**", "vendor/*"]
```

That is the surface. The docs cover the rest without repeating it here:

- [Configuration reference](https://lanorme.github.io/lanorme/latest/reference/configuration/):
  every key, its type and default, plus a machine-readable JSON schema.
- [Profiles (`extends`)](https://lanorme.github.io/lanorme/latest/how-to/use-profiles/):
  the `strict`, `hexagonal`, `clean` and `layered` bundles.
- [Per-directory config](https://lanorme.github.io/lanorme/latest/reference/configuration/):
  drop a nested `lanorme.toml` to tighten one subtree while the rest stays lenient.

## Adopting on an existing codebase

A mature codebase has findings on day one. A baseline records the debt you
already have so only *new* findings report; the whole adoption is two commands:

```console
lanorme baseline write    # records current findings to lanorme-baseline.json
```

Add `baseline = "lanorme-baseline.json"` under `[tool.lanorme]` and commit the
file like a lockfile. From then on every check runs at full strictness, but only
what you add reports. The full walkthrough is the
[adopt-on-an-existing-codebase tutorial](https://lanorme.github.io/lanorme/latest/tutorials/adopt-on-existing-codebase/).

## Writing a check

A check is any object with `name`, `description`, `rules`, and a `run` method;
drop it in `lanorme/checks/`, ship it under the `lanorme.checks` entry-point
group, or point at it with `[tool.lanorme] plugins = [...]`. The
[write-a-check guide](https://lanorme.github.io/lanorme/latest/how-to/write-a-check/) and
[`CONTRIBUTING.md`](CONTRIBUTING.md) cover the setup, the gates, and the
conventions for a new rule.

## Versioning

The public surface is the rule codes you put in `select` / `ignore` /
`per-file-ignores` and the config keys under `[tool.lanorme]`. The question that
decides a bump is whether a green codebase could go red on upgrade: a **patch**
keeps every result unchanged, a **minor** can newly fail a previously-passing
codebase (every pre-1.0 breaking change lands here), and a **major** is the
stability commitment. Every change is listed in [`CHANGELOG.md`](CHANGELOG.md).

## Licence

MIT. See [`LICENSE`](LICENSE).
