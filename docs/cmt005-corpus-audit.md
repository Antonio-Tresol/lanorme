# CMT005 Corpus Audit

Independent neutral-practitioner review of every label in
`tests/fixtures/comments_restating/labels.json`. The reviewer did not consult
the design doc, the detector implementation, the benchmark script, or any task
transcripts; only the fixture files and `labels.json` were used.

Working definition applied:

> A comment is RESTATING / REDUNDANT when reading it teaches a competent Python
> reviewer nothing they could not already get by reading the adjacent line of
> code (it paraphrases the *what* without adding *why*, *caveat*, *constraint*,
> *reference*, *unit*, or *non-obvious context*).
>
> A comment is OK / VALUABLE when it contributes anything beyond the code:
> rationale, warning, contract, units/format, reference, intent,
> disambiguation, or TODO/FIXME/etc.

## Summary

| Quantity                                              | Value |
|-------------------------------------------------------|------:|
| Total labelled comments                               |   122 |
| Of which corpus = `restating`                         |    51 |
| Of which corpus = `ok`                                |    71 |
| Reviewer agreements                                   |   121 |
| Reviewer disagreements                                |     1 |
| Agreement rate                                        | 99.2% |
| Disagreements where corpus says `restating`, reviewer says `ok` | 0 |
| Disagreements where corpus says `ok`, reviewer says `restating` | 1 |

The single disagreement is `neg_shared_vocab_borderline.py:43` (see table
below). Every other label survived neutral re-review.

## Disagreements

| File:line | Corpus label | Reviewer label | Reviewer rationale | Original corpus note |
|-----------|--------------|----------------|--------------------|----------------------|
| `negatives/neg_shared_vocab_borderline.py:43` | `ok` | `restating` | The adjacent line `retries = min(retries, 5)` already encodes both the identifier (`retries`), the operation (cap), and the literal bound (`5`). The comment `# retries capped at 5` is a pure paraphrase of the code with no added unit, contract, source, or rationale — structurally identical to the `pos_synonym_*` cases such as "double the amount" over `amount = amount * 2` or "increment the counter" over `counter += 1`, which the corpus correctly labels `restating`. | "shares 'retries' but adds the cap of 5" — but the cap of 5 is literally in the code as `min(retries, 5)`, so the comment adds nothing the code does not. |

## Bias diagnosis

### 1. The corpus is shaped around a specific detector class, not the neutral definition

The fixture docstrings openly advertise this:

- `positives/pos_inline_restatements.py`: *"the current detector only inspects standalone comments, so these are ground-truth positives it is guaranteed to miss"*
- `positives/pos_synonym_restatements.py`: *"a substring detector cannot see it … these are still redundant comments that should be flagged"*
- `negatives/neg_shared_vocab_hard.py`: *"the false positives a naive word-overlap detector is most likely to produce"*
- `negatives/neg_shared_vocab_borderline.py`: *"the corpus's stress test for precision … a pure word-overlap detector is liable to flag these; a good detector must not"*

The selection is therefore not a random sample of real-world comments; it is a
targeted precision/recall stress test for a token-overlap detector. The
per-label decisions are mostly defensible, but the *distribution* is heavily
biased toward:

- positives where comment ≈ code token (easy for a synonym/paraphrase detector
  to learn) and inline trailing comments (a known blind spot of one
  implementation), and
- negatives where the comment must overlap an identifier from the next line in
  order to be tricky for a word-overlap detector.

Whole categories of real-world borderline restatements are absent or
under-represented, e.g.:

- Comments that restate the *what* but happen to include one half-useful
  qualifier (e.g. `# loop over items in reverse to skip the header`).
- Stale comments — comments that once described different code and now mislead.
- Type/shape annotations spelled out in prose where a type hint already exists.
- Restatements that span a multi-line block rather than a single adjacent line.
- Doctring-vs-comment redundancy.

A detector tuned only against this corpus may look very good in benchmark
numbers and still under-perform on real codebases.

### 2. The `neg_shared_vocab_*` files are mostly written as "code-stub + meaningful comment"

In `neg_shared_vocab_hard.py` most function bodies are `x = x; return x` — the
code is intentionally trivial so that any informational content is forced into
the comment. This is fine for testing detector *precision*, but it slightly
flatters the "ok" label: in real code those same comments would often sit next
to richer logic where some of the comment's information leaks into adjacent
identifiers and helper names. The corpus does not stress-test the case where
the *code* already provides the unit/constraint and the comment merely
restates it. The one disagreement above (`# retries capped at 5` over
`min(retries, 5)`) is the only fixture line where the code actually does
encode the constraint, and the corpus still labels it `ok`. Suggested
correction: relabel `neg_shared_vocab_borderline.py:43` to `restating`, or
amend the surrounding code so the cap value lives only in the comment (e.g.
make `5` a configurable constant referenced symbolically).

### 3. Banner-rule lines are labelled OK as part of a header unit, not on their own merit

In `neg_section_headers.py`, lines 6, 8, 19, 21 are bare `# ----------` or
`# ==========` rules. Under a strict reading of the working definition, a line
that is only punctuation teaches a reviewer literally nothing — but it also is
not *restating* anything (there is no adjacent code line being paraphrased).
The corpus calls them `ok` ("banner rule above/below a section header"), which
is reasonable in context: the three-line block as a unit is a navigation aid,
and grading the middle line `# Public API` as OK while the surrounding rules
as restating would be perverse. I accept the corpus framing here, but flag
that a literal application of "teaches a reviewer nothing" would mark these
restating. Detectors should special-case header rules rather than rely on the
working definition to exclude them.

### 4. No systematic over- or under-flagging in either direction

With 121/122 agreement, there is no evidence that the corpus is systematically
biased toward one label. The single disagreement is in the direction of
*under*-flagging (a restating comment labelled `ok`), and even that one is
genuinely borderline.

## Honest list of borderline cases

These are cases where the reviewer agreed with the corpus label, but a
reasonable second reviewer could plausibly disagree. They are not corrections,
just transparency:

- **`positives/pos_synonym_more.py:25`** — `# open the file for writing` over
  `open("/tmp/out.txt", "w")`. The reviewer agrees this is restating because
  Python's `'w'` mode is well-known to any competent reviewer, but a reader
  who genuinely does not remember the single-letter mode strings could find
  it informative.
- **`positives/pos_synonym_more.py:10`** — `# check if the data is empty`
  over `if not data:`. Strictly a paraphrase, but `if not data` is also
  ambiguous (empty list, `None`, empty string, `0`); the comment commits to
  the "empty container" reading, which is mild disambiguation. Reviewer still
  scores it `restating` because the function signature `data: list[int]`
  already disambiguates.
- **`negatives/neg_shared_vocab_borderline.py:19`** — `# offset starts at 0`
  over `offset = offset`. A function parameter named `offset` in idiomatic
  Python is overwhelmingly zero-based already; the comment's constraint is
  weak. Reviewer accepts `ok` because not every API is zero-based and the
  comment forecloses ambiguity, but a stricter reviewer could call it
  restating.
- **`negatives/neg_section_headers.py:6, 8, 19, 21`** — bare banner rules.
  Accepted as `ok` under the "header unit" framing; would be `restating` (or
  perhaps better, a separate "noise" class) under a strictly literal reading
  of the working definition.
- **`negatives/neg_urls_refs.py:16`** — `# Works around cpython bug:
  https://bugs.python.org/issue12345` over `return value + 0`. The URL is
  clearly valuable, but the code (`+ 0`) is a no-op that any reviewer would
  question. Reviewer scores `ok` because the URL is the whole point; a strict
  reviewer could argue the *what* (the workaround) is so opaque that the
  comment is also restating something obvious about the no-op. Edge case.
- **`negatives/neg_warnings_invariants.py:39`** — `# noqa: S307`. Strictly a
  tool pragma rather than a comment in the prose sense; classifying it as
  `ok` under the "valuable comment" axis is mildly category-confused (it
  would be cleaner to live in `neg_pragmas.py`), but the labelling is not
  wrong.

## Suggested concrete label corrections

1. **`negatives/neg_shared_vocab_borderline.py:43`** — change `ok` to
   `restating`. The comment `# retries capped at 5` does not add information
   beyond `retries = min(retries, 5)`. Alternatively, change the code to
   `retries = min(retries, MAX_RETRIES)` so the literal `5` lives only in the
   comment; then `ok` is justified.

2. (Optional) Move `negatives/neg_warnings_invariants.py:39` (`# noqa: S307`)
   into `neg_pragmas.py` so the category boundaries stay clean. The label
   itself is correct.

3. (Optional) Add a small fixture file of *stale*/*misleading* comments and a
   file where comments restate code spread over several lines, to broaden the
   corpus beyond the single-line-overlap regime it currently tests.

## Corpus extension (round 2)

This extension addresses the structural-bias finding (§ "Bias diagnosis 1")
by adding the five categories the audit named as absent or
under-represented. Per-label decisions in the original 122 entries were
not modified; the suggested relabel of `neg_shared_vocab_borderline.py:43`
and the suggested move of `# noqa: S307` were intentionally left as
separate clean-ups so the round-1 numbers remain reproducible.

### New fixture files

| File | Category | Labels | Polarity |
|------|----------|-------:|----------|
| `positives/pos_half_useful_qualifier.py`   | A — half-useful qualifier (qualifier is in code) | 6 | restating |
| `negatives/neg_half_useful_qualifier.py`   | A — half-useful qualifier (qualifier carries new info) | 6 | ok |
| `positives/pos_stale_comment.py`           | B — stale / misleading comments | 6 | restating |
| `positives/pos_type_in_prose.py`           | C — type spelled in prose (type hint exists) | 6 | restating |
| `negatives/neg_type_in_prose.py`           | C — type-prose with a genuinely new property | 6 | ok |
| `positives/pos_multiline_restatement.py`   | D — multi-line block restatement | 5 | restating |
| `negatives/neg_multiline_restatement.py`   | D — multi-line block with emergent intent | 5 | ok |
| `positives/pos_docstring_dup.py`           | E — comment duplicates the enclosing docstring | 5 | restating |
| **Total**                                  |                                                       | **45** | 28 restating / 17 ok |

### New totals

| Quantity                       | Round 1 | Round 2 (after extension) |
|--------------------------------|--------:|--------------------------:|
| Total labelled comments        |     122 |                       167 |
| Of which `restating`           |      51 |                        79 |
| Of which `ok`                  |      71 |                        88 |

### Self-audit of the new labels

Every new label was re-checked against the working definition stated at
the top of this document, with the rule that any qualifier the comment
adds must NOT be recoverable from the adjacent code for the label to be
`ok`. **Flip count during self-audit: 0**. Two rounds of *fixture
rewrites* (not label flips) happened in `pos_half_useful_qualifier.py`
before locking labels: round 1 removed two comments that leaked
rationale absent from the code, round 2 (after a category-purity review)
tightened L20/L25/L30/L35/L40 so each carries a distinct
qualifier-clause that the adjacent code visibly encodes — matching the
canonical audit example `# loop over items in reverse to skip the
header` / `for item in reversed(items[1:]):`. No `restating`/`ok` label
in the committed JSON was changed after being committed.

### Scorer re-run

Command: `uv run python evals/score_cmt005.py`

| Metric    | Round 1 (122 labels) | Round 2 (167 labels) |
|-----------|---------------------:|---------------------:|
| TP        |                   33 |                   33 |
| FP        |                    0 |                    0 |
| FN        |                   18 |                   46 |
| TN        |                   71 |                   88 |
| Precision |                1.000 |                1.000 |
| Recall    |                0.647 |                0.418 |
| F1        |                0.786 |                0.589 |

### Interpretation

The detector retained perfect precision on the broadened corpus — every
new `ok` example (including the half-useful-qualifier twins, the
type-prose-with-units twins, and the emergent-intent multi-line summaries)
was correctly NOT flagged. Recall fell from 0.647 to 0.418 because the
detector misses the entirety of the five new restating categories
(half-useful qualifier, stale, type-in-prose, multi-line, docstring-dup).
The recall drop is the round-2 measurement of the structural bias the
audit warned about: the round-1 0.786 F1 was an upper bound for the
detector's blind spot, not its real-world performance. The 0.589 F1 is
not "a worse detector"; it is the same detector measured against a less
biased corpus.
