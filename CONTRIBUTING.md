# Contributing to LaNorme

Thanks for your interest. LaNorme is a standalone, standard-library-only linter
for Python: it checks the usual code-quality things plus a few that other
linters do not, such as hexagonal layer boundaries and a project's own naming
vocabulary. This guide covers the setup, the conventions, and how to add a rule.

## Principles

- **Standard library only.** No runtime dependencies. The only dev dependency
  is `pytest`. A change that adds a runtime dependency will not be accepted.
- **Precision over recall.** A noisy rule trains people to ignore the tool. New
  heuristics are expected to be high precision, with the noisy or debatable
  cases left out or gated behind config.
- **LaNorme lints itself.** There is no separate formatter or linter in the
  toolchain; `lanorme check .` is the style gate, and the repo passes its own
  rules.

## Setup

You need [`uv`](https://docs.astral.sh/uv/) and Python 3.13 or newer.

```console
uv sync --group dev
uvx pre-commit install     # run the linter and tests on every commit
```

The pre-commit hooks run `lanorme check .` and the unit tests, so a commit only
lands when the tree is LaNorme-compliant. `pre-commit` is fetched on demand with
`uvx`, so it is not added to the project dependencies (the only dev dependency
stays `pytest`).

## The gates

A change is ready when all three pass:

```console
uv run pytest tests/unit        # unit tests
uv run lanorme check .          # dogfood: exits 0 when the tree is clean
uv build                        # the package still builds
```

`lanorme check .` exits `1` on any failing rule. Advisory warnings (size,
complexity, and the like) keep the exit code at `0`, but please keep them down:
fix them by refactoring rather than by suppression where you reasonably can.

## Adding or changing a check

A check is any object with `name`, `description`, `rules`, and a `run` method.
An optional `configure` method receives its `[tool.lanorme.<name>]` table.

```python
from lanorme import CheckResult, Status, Violation, register


class MyCheck:
    name = "my_check"
    description = "What it enforces, in one line"
    rules = ["MYCODE-001: the rule, in one line"]

    def run(self, *, src_root: str) -> CheckResult:
        violations: list[Violation] = []
        # inspect files under src_root (use lanorme.discovery.iter_py_files)
        status = Status.FAIL if violations else Status.PASS
        return CheckResult(check=self.name, status=status, violations=violations)


register(MyCheck())
```

Drop the module in `src/lanorme/checks/`; it is discovered and registered
automatically. Third-party checks can instead ship under the `lanorme.checks`
entry-point group or be named in `[tool.lanorme] plugins = [...]`.

Conventions for a new rule:

- **Scan files through `lanorme.discovery.iter_py_files` / `iter_files`,** not
  `Path.rglob`, so the built-in directory pruning and the user's `exclude`
  globs are honoured.
- **One category prefix per check.** Rule codes (`SQL-001`, `LAYER-005`) are the
  public surface: people put them in `select` / `ignore` / `per-file-ignores`.
  Treat them as stable. Renaming or removing one is a breaking change.
- **Findings vs warnings.** Put a hard finding in `violations` (it fails the
  run); put an advisory in `warnings` (it reports but keeps exit 0). Advisory,
  opinionated, or stylistic rules should be warnings.
- **Default off when opinionated or broad.** If a rule is opinionated or fires
  often on ordinary code, ship it default-off (an `enabled` field, default
  `False`) and let users opt in. Decide the default by measuring the rule on
  representative third-party code (for example the standard library), not only
  on this repo.
- **Heuristic rules get a corpus.** A fuzzy detector should come with a labelled
  fixture set under `tests/fixtures/` and a scorer under `benchmarks/` that
  reports precision, recall, and F1, so the precision claim is measured.
- **Stay within the house limits.** LaNorme enforces its own `SIZE` / `PARAM` /
  `COMPLEXITY` limits on itself: files warn past 300 lines, functions past 50,
  cyclomatic complexity past 10, parameters past 5. Split helpers out rather
  than growing one function.

## Tests

Tests live in `tests/unit/` and are written in clear Arrange / Act / Assert
sections (LaNorme dogfoods its own `AAA` rules on them). Shared setup goes in
`tests/unit/conftest.py` so the per-test arrange blocks stay small. Add a
positive and a negative case for each rule you touch.

## Documentation

Docs state the current truth of the codebase and nothing else. History lives in
`CHANGELOG.md` only: do not write "previously", "was X now Y", or "split out
from" in `README.md`, `docs/RULES.md`, or docstrings. When you add or change a
rule, update its section in `docs/RULES.md` and the rule tables in `README.md`
in the same change. The Markdown is itself linted (British spelling, no em
dashes, no emoji), so run the dogfood after editing.

## Commits and pull requests

- Work on a branch, not `main`.
- Keep a change focused and describe the user-facing effect.
- Add a `## [Unreleased]` CHANGELOG entry for anything users would notice.

## Releasing (maintainers)

Releases are automated: creating a GitHub Release publishes to PyPI through
Trusted Publishing, no token required. Use `scripts/release.sh X.Y.Z` (see the
`release-lanorme` skill in `.claude/skills/`) after adding a `## [X.Y.Z]`
section to `CHANGELOG.md`.

## Licence

By contributing you agree that your work is released under the MIT licence (see
the `LICENSE` file).
