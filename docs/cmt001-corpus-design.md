# CMT-001 corpus design

Audit corpus and scoring harness for the CMT-001 "no commented-out code" check.
Built deliberately *without* reading the detector source, so that the labels
reflect a neutral working definition and not the detector's current behaviour.

## Working definition

> A comment is **COMMENTED_CODE** when it consists primarily of an executable
> Python statement (an import, assignment, call, definition, control-flow
> keyword, or expression statement) that a reasonable engineer would interpret
> as old/disabled code rather than as documentation.
>
> A comment is **OK** when it functions as prose, documentation, tooling
> pragma, reference, header, marker, or annotation — even if it textually
> overlaps Python syntax.

Labels are line-by-line on every `#` comment in every fixture file
(165 labels across 18 fixtures, no orphans — the scorer enforces this).

## Category split

### Positives (66 labels, 7 files)

| file                              | category                                  |
|-----------------------------------|-------------------------------------------|
| `pos_disabled_imports.py`         | disabled `import` / `from ... import`     |
| `pos_disabled_assignments.py`     | disabled simple and augmented assignments |
| `pos_disabled_calls.py`           | disabled call statements (log/metrics/debug) |
| `pos_disabled_control_flow.py`    | disabled `if/for/while/try/except` and bare `return`/`raise` |
| `pos_disabled_definitions.py`     | disabled `def`/`class`/decorator headers and bodies |
| `pos_disabled_block.py`           | contiguous multi-line disabled block      |
| `pos_inline_disabled.py`          | end-of-line `#` whose body is an alternative statement |

### Negatives (99 labels, 11 files — covers every category the task enumerates)

| file                              | category                                  |
|-----------------------------------|-------------------------------------------|
| `neg_todo_fixme.py`               | TODO/FIXME/XXX/HACK/NOTE task tags        |
| `neg_urls_refs.py`                | URL and citation references (docs, RFCs, issues, papers) |
| `neg_type_contracts.py`           | parameter/return/exception contract documentation |
| `neg_copyright_headers.py`        | copyright + Apache-2.0 license header block |
| `neg_shebang_encoding.py`         | shebang, PEP 263 encoding decl, vim modeline |
| `neg_section_banners.py`          | rule-and-title section banners and short markers |
| `neg_math_units.py`               | math/unit annotations next to numeric values |
| `neg_prose.py`                    | explanatory prose ending in `.` `?` `!`   |
| `neg_colon_annotations.py`        | colon-bearing prose ("key: value", "input:") |
| `neg_pragmas.py`                  | `# noqa`, `# type: ignore`, `# fmt: off`, `# pragma: no cover`, etc. |
| `neg_call_signatures.py`          | illustrative call signatures with `...` placeholders |

## Current-detector score

Run via `uv run python evals/score_cmt001.py`:

```
labels: 165 comments (66 commented_code / 99 ok)
TP: 44   FP: 1   FN: 22   TN: 98
PRECISION: 0.978
RECALL:    0.667
F1:        0.793
```

The detector is high-precision and recall-limited. The single FP and the
22 FN cluster into a small number of patterns.

## FP patterns (for the second team)

- **AST-parseability is treated as sufficient evidence of "disabled code"**,
  with no use of role-signaling context that real readers use to identify
  documentation. The lone FP — `# register("svc", timeout=30)` immediately
  after a `# Typical usage:` header — is the example. Falsifiable prediction
  for the second team: the other illustrative-signature lines in
  `neg_call_signatures.py` only escape because they contain `...`
  placeholders that appear to defuse a separate filter; remove the ellipses
  and the FP count should jump materially. A robust implementation would
  consult adjacent comments such as `Typical usage:` / `Signature:` /
  `Equivalent to:` / `Public surface:`.

## FN patterns (for the second team)

The 22 false negatives reduce to a **single generalizable failure mode**, not
22 independent bugs:

- **The detector appears to require the comment body to parse as a complete,
  standalone, top-level Python statement.** Anything that is syntactically
  valid only as part of a multi-line construct, or only inside an enclosing
  scope, slips through silently. Concretely the missed sub-patterns are:

  - Block headers ending in `:` — `if`, `elif`, `for`, `while`, `try`,
    `except`, `def`, `class`. None of these parse standalone (they need a
    body), so a parse-and-check approach rejects them all.
  - Decorator lines — `@cache`, `@staticmethod`, `@app.route(...)`, `@property`.
    A `@`-prefixed expression is not a standalone statement at module scope.
  - Bare `return` / `raise` outside a function — `# return result + 1`,
    `# raise`. These are SyntaxError at module scope even though they are
    obviously disabled code.

- **Implication for the next-most-valuable improvement**: a crude block-aware
  pass that recognises commented block headers, decorators, and scope-bound
  keywords as commented code (perhaps by attempting parse inside a synthetic
  `def`/`class` wrapper, or by pattern-matching the header forms) would
  recover most of the recall gap. Note the class-imbalance in the FN pool —
  control-flow headers alone are 16 of 22 — so the recall lift from one
  conceptual fix is large.

## Boundary cases acknowledged

These are the labels closest to the wall under the neutral definition. They
are kept as labelled, but the design notes them so the second team understands
where the corpus is making a judgement call rather than reading off an obvious
fact:

- `negatives/neg_call_signatures.py:9` — `# register("svc", timeout=30)` is a
  fully-parseable call. The label hinges on the `# Typical usage:` header two
  lines above. This is the boundary case the definition makes us live with.
- `positives/pos_disabled_definitions.py:20` — the bare `#` inside a disabled
  class is labelled `ok` because the line itself is not an executable
  statement. A future block-aware detector that correctly recognises the
  whole disabled class will be penalised for flagging this line; this is a
  known asymmetry between line-level labels and block-level intent, not a
  detector bug to chase.
- `negatives/neg_type_contracts.py:25` — `# fn: Callable[[int, str], bool]`
  parses as a valid module-level annotation. The label is `ok` because the
  primary purpose, in context, is parameter-contract documentation.
- `negatives/neg_colon_annotations.py:21–23` — `# environment: production`
  etc. parse as annotations. Labelled `ok` as module-level metadata prose.

## Process notes

- Brainstorm-categories-first, then-fixtures, then-labels was followed strictly.
- Per-file docstrings describe the comment's role in a real codebase
  ("disabled assignment statements", "TODO/FIXME task tags") and never
  reference what the detector might or might not do.
- Comment-line coverage was verified with a tokenize pass that errors on any
  `#` line missing from `labels.json`. The scorer enforces the same
  invariant from the other direction.

## Self-audit pass

A cold re-read of all 165 labels was performed: the labels were shuffled and
re-displayed with their assigned class but without their original notes, so
the original rationale could not anchor the re-judgement. **Flips: 0.** Four
labels were re-examined as boundary cases and are documented above as such;
none crossed the threshold for flipping under the neutral definition. The
zero count is reported honestly — the boundary cases are real, and the
discipline of writing each one up in the "Boundary cases acknowledged"
section is what the audit produced in lieu of flips.
