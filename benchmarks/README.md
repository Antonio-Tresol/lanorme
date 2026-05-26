# Benchmarks

Two scripts:

### `run_benchmarks.py`: reproducible end-to-end suite

Times a real `lanorme check <path>` process (what a user feels) over a
**version-pinned** set of real-world codebases, so results are comparable
across machines and over time.

```console
uv run python benchmarks/run_benchmarks.py          # all corpora
uv run python benchmarks/run_benchmarks.py --quick  # skip the large ones
uv run python benchmarks/run_benchmarks.py --runs 5
```

Canonical corpora (pinned): `requests==2.31.0`, `flask==3.0.0`, `rich==13.7.0`,
`sqlalchemy==2.0.23`, and the CPython standard library of the running
interpreter. PyPI sdists are downloaded once into `benchmarks/.corpora/`
(git-ignored) and cached; the stdlib is used in place.

### `bench.py`: per-check breakdown on one path

Times each check independently plus a single walk+parse baseline, to quantify
how much a shared parse cache *could* save (the cost/benefit of giving up check
independence).

```console
uv run python benchmarks/bench.py <path> [runs]
```
