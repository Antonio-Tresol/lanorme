---
name: release-lanorme
description: Use when cutting, shipping, releasing, or publishing a new LaNorme version (a "0.x.y" bump, a tag, a PyPI release). Runs every release gate (unit tests, the dogfood, generated docs in sync), records a eval audit (precision/recall/F1 per scored rule plus end-to-end performance, stamped with the version and hardware) to evals/results/, bumps the version, tags, and creates the GitHub Release that auto-publishes to PyPI and deploys the versioned docs.
license: MIT
compatibility: Requires Python 3.13+, uv, git, and gh, run from a clean main checkout.
metadata:
  project: lanorme
---

# Release LaNorme

This page explains how to cut a release and the discipline every release runs:
the gates, a recorded eval audit, regenerated docs, and the automated
publish. Creating a GitHub Release fires `.github/workflows/release.yml` (builds
and publishes to PyPI through Trusted Publishing, OIDC, no token handled) and
`.github/workflows/docs.yml` (deploys that version's docs with mike). `uv
publish` is never run by hand.

## The release discipline

Every release records the same evidence so a green tag is auditable later:

1. **Tests and dogfood** pass (`pytest tests/unit`, `lanorme check .`).
2. **Generated docs are in sync** with the tool (`scripts/gen_docs.py --check`):
   the configuration reference, JSON schema, rule index, and llms files.
3. **A eval audit is recorded** to `evals/results/vX.Y.Z.json`: the
   accuracy metrics (precision, recall, F1 per scored rule against the labelled
   corpora) and the end-to-end performance numbers, each stamped with the
   LaNorme version, the git commit, the Python version, and the hardware
   (platform and processor). Accuracy is deterministic and is the audit's
   backbone; performance is informative and machine-dependent (the hardware
   stamp is what makes it interpretable).
4. **RULES.md reflects the measured F1** for every rule that has a corpus. If a
   rule's F1 moved, update its line before tagging.

`scripts/release.sh` enforces steps 1 to 3 (it refuses to tag if any gate fails
or the docs are stale); step 4 is a human check on the audit output.

## Versioning

The public surface is the rule codes used in `select` / `ignore` /
`per-file-ignores` and the config keys under `[tool.lanorme]`. The deciding
question is whether a green codebase could go red on upgrade:

- patch (`0.y.z`): no existing codebase's result changes (fixes, docs, opt-in
  checks, new config keys with safe defaults).
- minor (`0.y.0`): a green codebase can newly fail (a new default-on check, a
  default-on rule made stricter, a renamed or removed rule code, a changed
  default). Before 1.0, every breaking change is a minor.
- major (`1.0.0`): the stability commitment.

The README "Versioning" section is canonical; keep them in step.

## Steps

1. Pick the new version `X.Y.Z`.
2. Add a `## [X.Y.Z]` section to `CHANGELOG.md` describing the user-facing
   changes. Required: the release notes are taken verbatim from it.
3. Regenerate the docs and review the audit numbers:

   ```
   uv run python scripts/gen_docs.py
   uv run python evals/audit.py --version X.Y.Z --output /tmp/preview.json
   ```

   Read the preview; if any F1 changed, update that rule's line in
   `docs/RULES.md`. Commit the regenerated docs and any RULES.md change. Do not
   commit the audit file yourself: `release.sh` records the committed
   `evals/results/vX.Y.Z.json` for you, against the release commit (step 4), so
   its version and commit stamp match the released tree.
4. From the repo root, run the helper:

   ```
   scripts/release.sh X.Y.Z
   ```

   It refuses unless you are on `main`, the CHANGELOG section exists, the docs
   are in sync, and the gates pass (including an eval-audit precheck that the
   corpora are not stale). Then it bumps the version in `pyproject.toml` and
   `src/lanorme/__init__.py`, builds, runs `twine check`, commits the release,
   records the eval audit against that commit (a second `Record X.Y.Z eval
   audit` commit), tags `vX.Y.Z`, pushes, and creates the GitHub Release.
5. Watch the publish and docs workflows, then verify the package is live:

   ```
   gh run watch $(gh run list --workflow=release.yml --limit 1 --json databaseId --jq '.[0].databaseId') --exit-status
   uvx --refresh --from lanorme==X.Y.Z lanorme --version
   ```

   The docs workflow publishes `X.Y.Z` (and moves the `latest` alias) at
   https://lanorme.github.io/lanorme/.

## Gotchas

- `scripts/release.sh` refuses to do anything unless you are on `main`, the
  working tree is clean, the `## [X.Y.Z]` CHANGELOG section exists, and the
  gates pass. It is safe to run; it tags nothing until every gate is green.
- The version lives in **two** files (`pyproject.toml` and
  `src/lanorme/__init__.py`); `release.sh` bumps both. The manual fallback must
  too, or the build and `lanorme --version` disagree.
- `uv publish` is never run by hand. PyPI publishing is OIDC Trusted Publishing,
  fired only by the GitHub Release.
- The eval audit's accuracy step is strict: if a scorer sees a finding that
  is not in its corpus `labels.json`, it errors rather than scoring a wrong
  number. That means a fixture went stale, not that the release is blocked on
  performance; fix the labels.
- Performance numbers are machine-dependent. The audit stamps the hardware so
  they are interpretable, but do not compare them across machines.

## If something fails

- A gate (tests, dogfood, stale docs) fails: nothing is committed or tagged. Fix
  and re-run.
- The eval audit's accuracy step fails (a scorer flags an unlabelled
  finding): the corpus is out of date. Fix the labels or the fixture, re-run.
- The publish workflow fails (for example a PyPI outage): the tag and release
  already exist, so do not re-tag. Re-run with `gh run rerun <id>` or
  `gh workflow run release.yml`.

## Manual fallback (no script)

Edit `CHANGELOG.md`, run `uv run python scripts/gen_docs.py`, `uv run --group
dev pytest tests/unit`, and `uv run lanorme check .`. Bump `version` in
`pyproject.toml` and `__version__` in `src/lanorme/__init__.py`, then `uv
build`, `git commit -m "Release X.Y.Z"`. Now record the audit against that
commit: `uv run python evals/audit.py --version X.Y.Z` and `git commit -m
"Record X.Y.Z eval audit" evals/results/`. Finally `git tag -a vX.Y.Z`, `git
push origin main`, `git push origin vX.Y.Z`, and `gh release create vX.Y.Z
dist/* --notes "..."`.
