# LaNorme

LaNorme makes a codebase standard executable. It is a precision-first,
stdlib-only Python linter that turns the rules your team has agreed on into
checks that run on every commit. It has zero runtime dependencies.

Precision comes first. A false positive is the cardinal sin: a check that
cries wolf trains people to ignore it, so LaNorme would rather stay silent
than flag code that is fine. Advisory findings are warnings until you choose
to make them build-failing.

## 30-second example

Install LaNorme as a development dependency:

```bash
uv add --dev lanorme
```

Or with pip:

```bash
pip install lanorme
```

Then check your project:

```bash
lanorme check .
```

A clean run reports that every check passed and exits `0`:

```text
All 25 checks passed.
```

Exit codes are `0` when clean, `1` when there are findings, and `2` on a
usage or configuration error, so the command drops straight into a pre-commit
hook or CI step.

Two shortcuts help while you work:

- `lanorme rule <CODE>` prints a single rule's reference section in the
  terminal, for example `lanorme rule DRY-001`.
- Appending `.md` to any page URL on this site returns that page as raw
  Markdown.

## Where to go next

- [Adopt LaNorme on an existing codebase](tutorials/adopt-on-existing-codebase.md):
  a tutorial that records a baseline so only new findings fail the build while
  existing debt stays visible.
- [How-to guides](how-to/index.md): task-focused recipes for promoting
  advisories, excluding paths, and wiring CI.
- Reference: the [configuration reference](reference/configuration.md) for
  every `[tool.lanorme]` key, and [the rules](RULES.md) for each check and its
  per-check settings.
- [Precision first](explanation/precision-first.md): why LaNorme treats a
  false positive as the cardinal sin, and what that costs and buys.
