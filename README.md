# LaNorme

> *La norme*: the standard.

A configurable, pluggable architecture & code-quality linter for Python.
Point it at any project and it enforces a floor of structural and hygiene
rules; opt in to stricter, project-specific rules through configuration; and
extend it with your own checks.

```console
$ lanorme check .
```

## Install

```console
# run without installing, straight from a built wheel
uv build
uvx --from dist/lanorme-*.whl lanorme check .

# or install as a tool
uv tool install .
lanorme check .
```

Requires Python 3.13+. Zero runtime dependencies (stdlib only).

## Usage

```console
lanorme check [PATHS...]            # run all enabled checks (default path: .)
lanorme check . --check=layer_deps  # run a single check by name
lanorme check . --select TYPE,SEC   # only these rule codes/categories
lanorme check . --ignore NAMING-003 # skip specific rules
lanorme check . --output-format json
lanorme rules                       # list every registered rule
```

Exit code is `1` when any check fails, `0` when clean.

## Configuration

LaNorme discovers configuration by walking up from the target path: a dedicated
`lanorme.toml` takes precedence, otherwise a `[tool.lanorme]` table in
`pyproject.toml`. CLI flags override config.

```toml
[tool.lanorme]
select = ["ALL"]                            # rule codes/categories to run
ignore = ["NAMING-003"]                     # rule codes/categories to skip
plugins = ["myproject.checks.house_rules"]  # extra check modules to load

# Per-check configuration (each table is handed to that check):
[tool.lanorme.stray_artifacts]
extensions = [".zip", ".pdf"]               # also flag these as stray (ART-002)
allow = ["docs/diagram.png"]                # never flag these (globs)

[tool.lanorme.forbidden_paths]
dirs = ["legacy_src", "build_artifacts"]    # these directories must not exist

[tool.lanorme.stale_paths]
tokens = ["src/", "old_pkg/"]               # flag references to these path tokens

[[tool.lanorme.domain_terms.rules]]
id = "TERM-001"
canonical = "Account"
forbidden = ["Acct", "Acnt"]
```

## Checks

**Always on** (universal hygiene, sensible defaults):
`duplication`, `file_limits`, `named_args`, `naming_consistency`,
`pattern_divergence`, `security_patterns`, `strong_types`, `test_coverage`,
`stray_artifacts` (flags screenshots/scratch/OS-junk clutter), and `meta`
(validates that every check emits well-formed output).

**Opt-in** (reusable mechanism, inert by default; they surface findings only
once per-check configuration lands, or where their target layout already
exists, e.g. `layer_deps` on a project with `domain/ application/ …`):
`forbidden_paths`, `stale_paths`, `domain_terms`, `layer_deps`, `port_coverage`.

## Writing a check

A check is any object implementing the `Check` protocol:

```python
from lanorme import CheckResult, Status, Violation, register


class MyCheck:
    name = "my_check"
    description = "What it enforces"
    rules = ["MYCODE-001: the rule, in one line"]

    def run(self, *, src_root: str) -> CheckResult:
        violations: list[Violation] = []
        # ... inspect files under src_root ...
        status = Status.FAIL if violations else Status.PASS
        return CheckResult(check=self.name, status=status, violations=violations)


register(MyCheck())
```

Drop the module into `lanorme/checks/` (built-in) or ship it in a package that
advertises it under the `lanorme.checks` entry-point group, or point at it from
`[tool.lanorme] plugins = [...]`. LaNorme discovers and runs it automatically.

## License

MIT

