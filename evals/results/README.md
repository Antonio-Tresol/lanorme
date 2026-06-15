# Release audit results

This directory holds one JSON file per release, named `v<version>.json`,
written by [`../audit.py`](../audit.py). Each file is committed as the audit
trail for that release: a durable record of how LaNorme's heuristic rules scored
against their labelled corpora at the moment of cutting the version. The
`git_commit` and `git_dirty` fields pin the exact dataset and code that produced
the numbers.

## Schema

Every file has three top-level keys.

- `metadata`: the version and hardware stamp. It records `audited_version`,
  `lanorme_version`, `git_commit`, `git_dirty`, `python_version`, `platform`,
  `processor` and `timestamp_utc`.
- `accuracy`: a list with one entry per scorer. A scored entry carries `rule`,
  `corpus`, `tp`, `fp`, `fn`, `tn`, `precision`, `recall` and `f1`. A scorer
  whose corpus has gone stale records `rule` and an `error` message instead of
  the numbers.
- `performance`: a map from corpus name to its end-to-end timing, or an empty
  map when the run used `--no-perf`. A corpus that could not be downloaded is
  recorded as skipped rather than failing the audit.

## Reading the numbers

The `accuracy` block is deterministic: the same code over the same labelled
corpora yields the same precision, recall and F1 on any machine, so these
numbers are directly comparable across releases. The `performance` block is
machine-dependent, so always read it against the hardware stamp in `metadata`
(`platform`, `processor`, `python_version`) before comparing timings.
