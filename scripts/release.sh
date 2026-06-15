#!/usr/bin/env bash
# Release helper for LaNorme.
#
# Usage: scripts/release.sh X.Y.Z
#
# Runs the gates, bumps the version, then commits, tags, and creates the
# GitHub Release. The release event triggers the PyPI Trusted Publishing
# workflow (.github/workflows/release.yml), so this script never calls
# `uv publish` and never touches a token.
set -euo pipefail

VERSION="${1:-}"
if [[ ! "$VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
  echo "usage: scripts/release.sh X.Y.Z" >&2
  exit 2
fi
TAG="v$VERSION"

cd "$(git rev-parse --show-toplevel)"

# --- preflight -------------------------------------------------------------
branch="$(git rev-parse --abbrev-ref HEAD)"
[[ "$branch" == "main" ]] || { echo "refusing: not on main (on $branch)" >&2; exit 1; }
if ! grep -q "^## \[$VERSION\]" CHANGELOG.md; then
  echo "refusing: CHANGELOG.md has no '## [$VERSION]' section. Add release notes first." >&2
  exit 1
fi
if git rev-parse "$TAG" >/dev/null 2>&1; then
  echo "refusing: tag $TAG already exists" >&2
  exit 1
fi

# --- gates (version-independent, so a failure leaves the tree untouched) ----
uv run --group dev pytest tests/unit -q
uv run lanorme check .            # dogfood: nonzero exit on any FAIL
uv run python scripts/gen_docs.py --check   # docs in sync: fail if generated docs are stale
# eval audit precheck: validate the labelled corpora are not stale before we
# touch the tree (a stale fixture must block the release here, while the failure
# still leaves the tree untouched). The recorded audit is written later, against
# the release commit, so its version and commit stamp match the released tree.
uv run python evals/audit.py --version "$VERSION" --no-perf --output "$(mktemp)"

# --- bump the version (portable in-place edit) ------------------------------
perl -i -pe "s/^version = .*/version = \"$VERSION\"/" pyproject.toml
perl -i -pe "s/^__version__ = .*/__version__ = \"$VERSION\"/" src/lanorme/__init__.py
echo "bumped to $VERSION"

# --- build and validate the artifacts --------------------------------------
rm -rf dist && uv build
uv run --with twine python -m twine check dist/*

# --- take the release notes from this version's CHANGELOG section -----------
notes="$(awk -v v="## [$VERSION]" '
  $0==v {grab=1; next}
  grab && /^## \[/ {exit}
  grab {print}
' CHANGELOG.md)"

# --- commit the release, then record the audit against that commit ----------
echo "--- changes to be released ---"
git status --short
git add -A
git commit -m "Release $VERSION"

# Record the eval audit against the just-made release commit, so its
# lanorme_version, git_commit and git_dirty stamp match the released tree
# (the installed __version__ is now bumped and the working tree is clean).
uv run python evals/audit.py --version "$VERSION" --no-perf
git add evals/results/
git commit -m "Record $VERSION eval audit"

git tag -a "$TAG" -m "$TAG"
git push origin main
git push origin "$TAG"
gh release create "$TAG" \
  "dist/lanorme-$VERSION-py3-none-any.whl" \
  "dist/lanorme-$VERSION.tar.gz" \
  --title "$TAG" \
  --notes "$notes"

echo
echo "Released $TAG. Watch the publish workflow:"
echo "  gh run watch \$(gh run list --workflow=release.yml --limit 1 --json databaseId --jq '.[0].databaseId') --exit-status"
echo "Then verify on PyPI:"
echo "  uvx --refresh --from lanorme==$VERSION lanorme --version"
