# Evals

This directory measures **how good** LaNorme's heuristic rules are: their
precision, recall and F1 against labelled corpora. It is separate from two
neighbours it is easy to confuse with:

- `tests/` answers *is it correct?* (a behaviour passes or fails).
- `benchmarks/` answers *how fast?* (end-to-end timing).
- `evals/` answers *how good is the heuristic?* (a quality score, not a verdict).

A rule like CMT-001 or SECRETPY-001 is a judgement call, not a theorem, so the
honest measure is a score on real examples, not a single pass/fail.

## Layout

```
evals/
  score_<rule>.py     one scorer per rule, exposing score()
  corpora/<name>/      a labelled corpus, with a labels.json ground truth
  audit.py             runs every scorer, writes a stamped result JSON
  results/v<x>.json    one committed audit per release (the trail)
```

Each scorer pairs with one corpus under `corpora/`. The corpus is the dataset;
the scorer is the code that grades the rule against it.

## The scorer interface

Every `score_<rule>.py` exposes a uniform entry point:

```python
def score() -> dict:
    """Return {rule, corpus, tp, fp, fn, tn, precision, recall, f1}.

    Raises ValueError if the corpus is stale (a finding on a file that
    labels.json does not cover), naming the offending file:line.
    """
```

It also defines a module-level `RULE` constant (the rule code it measures) so
the audit can label a result even when `score()` raises. Running a scorer
directly prints a human-readable report:

```console
uv run python evals/score_cmt001.py
```

## The audit

`audit.py` discovers every `score_*.py`, calls `score()`, and writes a single
result JSON stamped with the version, git commit, dirty flag and hardware, so a
release carries a durable, reproducible record of its accuracy:

```console
uv run python evals/audit.py --version X.Y.Z [--no-perf]
```

The release gate runs this automatically (see the `release-lanorme` skill), so
every tagged version leaves a `results/v<version>.json` behind. The `git_commit`
and `git_dirty` fields pin the exact dataset and code that produced the numbers;
the `accuracy` block is deterministic and comparable across releases. See
[`results/README.md`](results/README.md) for the full schema.

## Adding an eval

1. Add a labelled corpus under `corpora/<name>/` with a `labels.json` ground
   truth.
2. Add `score_<rule>.py` exposing `score()` and a `RULE` constant, reading the
   corpus from `Path(__file__).resolve().parent / "corpora" / "<name>"`.
3. Run `uv run python evals/audit.py --version 0.0.0-test --no-perf` to confirm
   it is discovered and scores cleanly.

The corpora are deliberately dirty (they exist to be flagged), so they are
excluded from the dogfood in `pyproject.toml`.
