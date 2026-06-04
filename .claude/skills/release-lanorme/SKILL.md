---
name: release-lanorme
description: Cut a new LaNorme release. Bumps the version, runs the gates, tags, and creates the GitHub Release, which auto-publishes to PyPI via Trusted Publishing. Use when asked to release, ship, or publish a new LaNorme version.
---

# Release LaNorme

Releases are automated end to end. Creating a GitHub Release fires
`.github/workflows/release.yml`, which builds and publishes to PyPI through
Trusted Publishing (OIDC). No token is ever handled, and `uv publish` is never
run by hand.

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

The README "Versioning" section is the canonical statement; keep them in step.

## Steps

1. Pick the new version `X.Y.Z`.
2. Add a `## [X.Y.Z]` section to `CHANGELOG.md` describing the user-facing
   changes. This is required: the release notes are taken verbatim from it.
3. From the repo root, run the helper:

   ```
   scripts/release.sh X.Y.Z
   ```

   It refuses unless you are on `main` and the CHANGELOG section exists. Then it
   runs the unit tests and the dogfood (`lanorme check .`), bumps the version in
   `pyproject.toml` and `src/lanorme/__init__.py`, builds, runs `twine check`,
   commits, tags `vX.Y.Z`, pushes, and creates the GitHub Release.
4. Watch the publish workflow and verify the package is live:

   ```
   gh run watch $(gh run list --workflow=release.yml --limit 1 --json databaseId --jq '.[0].databaseId') --exit-status
   uvx --refresh --from lanorme==X.Y.Z lanorme --version
   ```

## If something fails

- Tests or dogfood fail: nothing is committed or tagged. Fix and re-run.
- The publish workflow fails (for example a PyPI outage): the tag and release
  already exist, so do not re-tag. Re-run with `gh run rerun <id>` or
  `gh workflow run release.yml`.

## Manual fallback (no script)

Do the same by hand: bump `version` in `pyproject.toml` and `__version__` in
`src/lanorme/__init__.py`, edit `CHANGELOG.md`, run
`uv run --group dev pytest tests/unit` and `uv run lanorme check .`, then
`uv build`, `git commit`, `git tag -a vX.Y.Z`, `git push origin main`,
`git push origin vX.Y.Z`, and
`gh release create vX.Y.Z dist/* --notes "..."`.
