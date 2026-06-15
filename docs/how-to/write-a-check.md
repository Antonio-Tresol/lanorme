# Write a custom check

This guide shows how to add your own rule to LaNorme as a plugin: a small Python
module that registers a check, which LaNorme then discovers and runs alongside
the built-ins. Use it to encode a house rule the bundled _normes_ do not cover,
your domain vocabulary, a project-specific structural invariant, or any
mechanical standard your team agrees on.

You do not fork LaNorme. A check is an ordinary object; you ship it in your own
package and point LaNorme at it.

## The Check protocol

A check is any object with four members:

- `name` (str): a unique identifier, used by `--check <name>` and in output.
- `description` (str): one line describing what the check enforces.
- `rules` (list of str): one entry per rule code, each `"CODE-001: one line"`.
- `run(self, *, src_root: str) -> CheckResult`: scans the tree and returns the
  findings.

`run` is keyword-only on `src_root` (the path being checked, as a string). It
returns a `CheckResult` carrying two lists of `Violation`: `violations` (hard
findings that fail the build) and `warnings` (advisories that report but keep the
exit code at `0`).

```python
from lanorme import CheckResult, Status, Violation


class MyCheck:
    name = "my_check"
    description = "What it enforces, in one line"
    rules = ["MYCODE-001: the rule, in one line"]

    def run(self, *, src_root: str) -> CheckResult:
        violations: list[Violation] = []
        # inspect files under src_root
        status = Status.FAIL if violations else Status.PASS
        return CheckResult(check=self.name, status=status, violations=violations)
```

A `Violation` records where and what:

```python
Violation(
    file="src/utils.py",   # path, relative to src_root
    line=12,               # 1-based line, or 0 for a whole-file or path finding
    rule="MYCODE-001: the rule, in one line",  # or just the bare code
    message="What is wrong here",
    fix="What to do about it",
)
```

The rule code is parsed from the `rule` string (everything before the first
colon), so a `Violation` may carry either the full `"MYCODE-001: ..."` string or
just `"MYCODE-001"`.

## Register the check

Call `register()` with an instance at import time. That is what makes LaNorme
find and run it.

```python
from lanorme import register

register(MyCheck())
```

A check that reads configuration may also implement `configure(self, *,
settings)`, which receives its `[tool.lanorme.<name>]` table before the run. See
[Configuring a check](#configuring-a-check) below.

## Scan files through discovery

Iterate files with `lanorme.discovery.iter_py_files` (or `iter_files` for other
suffixes), never `Path.rglob`. The discovery helpers prune the built-in
never-source directories (`.venv`, `node_modules`, `__pycache__`, `dist`,
`build`, and the rest) and honour the user's `exclude` globs at walk time, so an
excluded subtree is never read. A raw `Path.rglob` would walk into a virtualenv
and report findings the user asked to exclude.

```python
from pathlib import Path

from lanorme.discovery import iter_py_files

for path in iter_py_files(Path(src_root)):
    ...  # path is a Path to a *.py file under src_root
```

`iter_files(root, suffix=".md")` does the same for any suffix.

## Conventions

These conventions keep a custom check consistent with the built-ins. The same
rules apply whether the check ships inside LaNorme or as your plugin.

- **One category prefix per check.** A check owns a single rule-code family
  (`MYCODE-001`, `MYCODE-002`, ...). Codes are the public surface: people put
  them in `select`, `ignore`, and `per-file-ignores`, so treat them as stable.
- **Hard findings in `violations`, advisories in `warnings`.** A `violations`
  entry fails the run (exit code `1`); a `warnings` entry reports but leaves the
  exit code at `0`. Opinionated or stylistic rules belong in `warnings`, so a
  user can promote them to errors when they choose (see
  [`promote`](../reference/configuration.md#promote)).
- **Set the status to match.** Return `Status.FAIL` when `violations` is
  non-empty, `Status.WARN` when only `warnings` is, otherwise `Status.PASS`.
- **Cross-file checks declare `scope = "tree"`.** If a finding depends on
  comparing or aggregating across files, set the class attribute `scope =
  "tree"`. The default `"file"` scope lets a check run once per config region
  under per-directory configuration; a tree-scoped check runs once at the scan
  root so a finding split across two regions is not missed.
- **Default off when opinionated or broad.** A rule that fires often on ordinary
  code should ship default-off behind an `enabled` flag, so users opt in (see
  [Configuring a check](#configuring-a-check)).

A check must never let an exception escape `run`; LaNorme isolates a crashing
check and reports it as a warning so one bug cannot sink the whole run, but a
clean check should not rely on that safety net.

## A worked example

This check fails when a module is named exactly `utils.py`, on the house rule
that every module should be named after what it does.

```python
# house_rules.py
from __future__ import annotations

from pathlib import Path

from lanorme import CheckResult, Status, Violation, register
from lanorme.discovery import iter_py_files


class NoUtilsModule:
    name = "no_utils_module"
    description = "Modules must have a meaningful name, not 'utils'"
    rules = ["HOUSE-001: Module must not be named 'utils.py'"]

    def run(self, *, src_root: str) -> CheckResult:
        violations: list[Violation] = []
        for path in iter_py_files(Path(src_root)):
            if path.name == "utils.py":
                violations.append(
                    Violation(
                        file=str(path.relative_to(src_root)),
                        line=0,
                        rule=self.rules[0],
                        message="Module named 'utils.py' has no clear responsibility",
                        fix="Rename it after what it actually does",
                    )
                )
        status = Status.FAIL if violations else Status.PASS
        return CheckResult(check=self.name, status=status, violations=violations)


register(NoUtilsModule())
```

With `house_rules.py` importable (on `sys.path` or installed), load it with
`--plugin` and run it:

```console
$ lanorme check src/ --plugin house_rules --check no_utils_module
[FAIL] no_utils_module
  VIOLATION: utils.py:0 - Module named 'utils.py' has no clear responsibility
    Rule: HOUSE-001: Module must not be named 'utils.py'
    Fix: Rename it after what it actually does
--- no_utils_module: 1 violations, 0 warnings ---
```

The exit code is `1`. Rename or remove the file and the run is clean:

```console
$ lanorme check src/ --plugin house_rules --check no_utils_module
All 1 checks passed.
```

The exit code is `0`.

>!!! note
>    `--plugin` is repeatable (`--plugin a --plugin b`), not comma-separated.
>    Pass the dotted module path, for example `--plugin myproject.checks.house_rules`.

### Make it an advisory

To report without failing the build, put findings in `warnings` and return
`Status.WARN`:

```python
        status = Status.WARN if warnings else Status.PASS
        return CheckResult(check=self.name, status=status, warnings=warnings)
```

The run then exits `0` and the check shows as `[WARN]`. A user who wants it to
fail the build can escalate the code with
[`promote`](../reference/configuration.md#promote):

```console
$ lanorme check src/ --plugin todo_advisory --promote TODO-001
```

That turns the advisory into a build-failing error (exit code `1`). `promote =
["ALL"]` escalates every advisory at once.

## Loading the plugin

LaNorme has three ways to load a plugin module so its `register()` call runs.
Choose one.

### Name it in config

List the module under `plugins` in `[tool.lanorme]`. LaNorme imports each named
module before the run, so the check self-registers:

```toml
[tool.lanorme]
plugins = ["myproject.checks.house_rules"]
```

This is the usual choice for a check that lives in your own repository. The
[`plugins` reference](../reference/configuration.md#plugins) documents the key.

### Ship it under the entry-point group

A distributable package can advertise its check module under the
`lanorme.checks` entry-point group. Any environment that installs the package
then has the check available with no per-project config:

```toml
# in the plugin package's pyproject.toml
[project.entry-points."lanorme.checks"]
house-rules = "myproject.checks.house_rules"
```

The entry-point value is the dotted module path; LaNorme imports it on every run.

### Pass it on the command line

Use `--plugin` for a one-off run, a quick experiment, or CI wiring that prefers
explicit flags over config:

```console
$ lanorme check src/ --plugin myproject.checks.house_rules
```

CLI flags override config, so `--plugin` adds to whatever `plugins` already
lists.

## Configuring a check

To accept settings from a `[tool.lanorme.<name>]` table, implement an optional
`configure` method. LaNorme hands it the table (a dict) before the run.

```python
from dataclasses import dataclass, field


@dataclass
class StrayExtensions:
    name: str = "stray_extensions"
    description: str = "Flag unwanted file extensions in the tree"
    enabled: bool = False
    extensions: tuple[str, ...] = ()
    rules: list[str] = field(
        default_factory=lambda: ["HOUSE-002: Unwanted file extension"]
    )

    def configure(self, *, settings: dict[str, object]) -> None:
        self.enabled = bool(settings.get("enabled", self.enabled))
        exts = settings.get("extensions")
        if isinstance(exts, list):
            self.extensions = tuple(exts)

    def run(self, *, src_root: str) -> CheckResult:
        ...
```

A user then configures it under the check's own table, named after `self.name`:

```toml
[tool.lanorme.stray_extensions]
enabled = true
extensions = [".zip", ".tmp"]
```

An opt-in check defaults `enabled` to `false` and returns `Status.PASS` with no
findings until the table sets `enabled = true`. That keeps a broad or opinionated
rule inert on a project that has not asked for it.

## Verify it is loaded

Run the check and confirm it executed. `--output-format full` shows passing
checks too, so a loaded check appears even when it found nothing:

```console
$ lanorme check . --plugin myproject.checks.house_rules --output-format full
```

For a check loaded via config or the entry-point group, drop the `--plugin`
flag — plain `lanorme check . --output-format full` lists it once it is
registered. Seeing your check in that output (a `[PASS]` line when it is clean)
is the reliable signal that the plugin loaded. For machine-readable output while
developing, use `--output-format ndjson` (one finding per line) or
`--output-format json` (one object per check).

`lanorme rules` is a narrower check. It lists only rules registered through the
`lanorme.checks` entry-point group, so it surfaces a plugin shipped that way but
not one loaded via `[tool.lanorme] plugins` or `--plugin`. The `rules` command
also takes no `--plugin` flag.

## Related pages

- [Configuration reference](../reference/configuration.md): every
  `[tool.lanorme]` key, including `plugins`, `select`, `ignore`, and `promote`.
- [Rule reference](../RULES.md): what each built-in rule catches and how to
  configure it; a model for documenting your own.
