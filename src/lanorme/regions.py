"""Cascading per-directory configuration (issue #28).

A *region* is a directory carrying a LaNorme config file (``lanorme.toml`` or a
``pyproject.toml`` with a ``[tool.lanorme]`` table) whose settings govern the
files beneath it. A nested region inherits its parent's settings and overrides
only the keys it sets, so a subtree can tighten or relax a rule without
restating the whole config. ``root = true`` in a region's config stops the
inheritance, letting a subtree stand alone (the eslint convention).

The runner uses this to lint an ageing codebase gradually: strict rules in the
new module, lenient rules in the legacy tree, tightening outward over time.

Two kinds of check resolve differently:

- **File-level** checks (size, naming, types, secrets, prose, ...) judge each
  file on its own, so each file is checked under the config of its nearest
  region. The runner scopes a region's pass to its own files by excluding the
  nested regions below it.
- **Whole-tree** checks (``duplication``, ``test_coverage``, the architecture
  checks ``layer_deps`` / ``port_coverage``, and the ``meta`` self-check)
  compare or aggregate across files, so partitioning them by region would hide
  a duplicate pair split across two regions. They run once at the scan root
  under the root config. A region therefore cannot relax a whole-tree check for
  its own subtree; that is documented behaviour.

A check declares itself whole-tree with a class attribute ``scope = "tree"``;
the default is ``"file"``.

Cascading governs check *configuration* (the ``[tool.lanorme.<check>]`` tables,
``source_root``, and the flags configurable checks expose). The run-level
filters (``select`` / ``ignore`` / ``exclude`` / ``per-file-ignores``) stay
root-level and are applied once by the CLI pipeline.
"""

from __future__ import annotations

import copy
import os
import tomllib
from collections.abc import Callable
from dataclasses import dataclass, field, replace
from pathlib import Path

from lanorme import Check, CheckResult, Status, Violation
from lanorme.discovery import DEFAULT_PRUNE_DIRS

# A loaded TOML config: string keys to arbitrary scalar / list / table values.
Config = dict[str, object]


def load_lanorme_config(directory: Path) -> Config | None:
    """Return the LaNorme config declared in *directory*, or ``None`` if none.

    A dedicated ``lanorme.toml`` wins over a ``pyproject.toml`` ``[tool.lanorme]``
    table, mirroring the walk-up discovery in the CLI. A ``pyproject.toml``
    without that table is not a config source and yields ``None``.
    """
    dedicated = directory / "lanorme.toml"
    if dedicated.is_file():
        with dedicated.open("rb") as handle:
            return tomllib.load(handle)

    pyproject = directory / "pyproject.toml"
    if pyproject.is_file():
        with pyproject.open("rb") as handle:
            data = tomllib.load(handle)
        tool_config = data.get("tool", {}).get("lanorme")
        if isinstance(tool_config, dict):
            return tool_config

    return None


def merge_config(*, base: Config, override: Config) -> Config:
    """Merge *override* onto *base*, override winning, recursing into sub-tables.

    Scalars and lists in *override* replace those in *base*; nested tables (a
    per-check ``[tool.lanorme.<name>]`` block) merge key by key, so a region can
    set one threshold and inherit the rest.
    """
    merged = dict(base)
    for key, value in override.items():
        existing = merged.get(key)
        if isinstance(existing, dict) and isinstance(value, dict):
            merged[key] = merge_config(base=existing, override=value)
        else:
            merged[key] = value
    return merged


@dataclass
class Region:
    """A directory whose config governs the files beneath it (nearest wins)."""

    directory: Path
    raw: Config
    merged: Config = field(default_factory=dict)

    @property
    def is_root(self) -> bool:
        """True when this region stops inheritance (``root = true``)."""
        return bool(self.raw.get("root"))


def _strip_root(config: Config) -> Config:
    """Return *config* without the ``root`` cascade-control key."""
    return {key: value for key, value in config.items() if key != "root"}


def _nearest_ancestor(*, directory: Path, candidates: list[Region]) -> Region | None:
    """Return the region whose directory is the closest proper ancestor of *directory*."""
    best: Region | None = None
    for candidate in candidates:
        if candidate.directory == directory:
            continue
        if candidate.directory in directory.parents:
            if best is None or len(candidate.directory.parts) > len(best.directory.parts):
                best = candidate
    return best


def discover_regions(
    *,
    scan_root: Path,
    root_config: Config,
    resolve_extends: Callable[..., Config] | None = None,
) -> list[Region]:
    """Resolve the tree under *scan_root* into config regions, root region first.

    The root region is *scan_root* under *root_config* (already discovered by the
    CLI's walk-up). Nested regions are directories strictly below *scan_root* that
    carry their own config file, with default-pruned directories skipped. Each
    region's ``merged`` config folds its ancestor chain top-down, stopping at the
    nearest ``root = true``.

    *resolve_extends*, when supplied, expands each nested region's ``extends`` the
    same way the CLI expands the root's, relative to the region's own directory,
    so a subtree can adopt a profile. The root config is already resolved by the
    caller.
    """
    scan_root = scan_root.resolve()
    regions = [Region(directory=scan_root, raw=root_config)]

    for dirpath, dirnames, _filenames in os.walk(scan_root):
        dirnames[:] = sorted(name for name in dirnames if name not in DEFAULT_PRUNE_DIRS)
        here = Path(dirpath).resolve()
        if here == scan_root:
            continue
        config = load_lanorme_config(here)
        if config:
            if resolve_extends is not None:
                config = resolve_extends(config=config, project_root=here)
            regions.append(Region(directory=here, raw=config))

    regions.sort(key=lambda region: len(region.directory.parts))
    for region in regions:
        region.merged = _resolve_merged(region=region, regions=regions)
    return regions


def _resolve_merged(*, region: Region, regions: list[Region]) -> Config:
    """Fold *region*'s ancestor chain into one config, stopping at ``root = true``."""
    chain: list[Region] = []
    node: Region | None = region
    while node is not None:
        chain.append(node)
        if node.is_root:
            break
        node = _nearest_ancestor(directory=node.directory, candidates=regions)

    merged: Config = {}
    for ancestor in reversed(chain):
        merged = merge_config(base=merged, override=_strip_root(ancestor.raw))
    return merged


def child_exclude_globs(*, region: Region, regions: list[Region]) -> list[str]:
    """Globs (relative to *region*) that prune every nested region below it.

    Running a region's file-level pass with these excludes scopes it to the files
    it directly governs: each nested region's subtree is left to that region. The
    globs are matched by ``fnmatch`` where ``*`` spans ``/``, so ``sub`` prunes the
    directory and ``sub/*`` prunes everything under it.
    """
    globs: list[str] = []
    for candidate in regions:
        if candidate.directory == region.directory:
            continue
        if region.directory in candidate.directory.parents:
            relative = candidate.directory.relative_to(region.directory).as_posix()
            globs.append(relative)
            globs.append(f"{relative}/*")
    return globs


def is_tree_scoped(check: Check) -> bool:
    """True when *check* compares across files and must run once at the scan root."""
    return getattr(check, "scope", "file") == "tree"


def snapshot_defaults(checks: dict[str, Check]) -> dict[str, Config]:
    """Capture each check's declared defaults so the runner can reset between regions.

    Checks are configured-once singletons whose ``configure()`` mutates instance
    attributes in place and never resets them, so running regions in sequence
    would leak one region's settings into the next. The defaults are read from a
    freshly constructed instance rather than the live one: across repeated CLI
    invocations in a single process (the test suite, a server) the live singleton
    is already configured from an earlier run, so its state is not pristine. A
    check that cannot be reconstructed with no arguments falls back to its current
    state.
    """
    snapshot: dict[str, Config] = {}
    for name, check in checks.items():
        try:
            defaults = type(check)().__dict__
        except Exception:  # noqa: BLE001 - an exotic check keeps its current state
            defaults = check.__dict__
        snapshot[name] = copy.deepcopy(defaults)
    return snapshot


def restore_defaults(*, checks: dict[str, Check], snapshot: dict[str, Config]) -> None:
    """Reset each check's instance state to the captured pristine snapshot."""
    for name, check in checks.items():
        if name in snapshot:
            check.__dict__.clear()
            check.__dict__.update(copy.deepcopy(snapshot[name]))


def combine_results(*, existing: CheckResult | None, addition: CheckResult) -> CheckResult:
    """Fold one region's result for a check into the running total for that check.

    A file-level check runs once per region, so its findings arrive in pieces;
    this concatenates them and recomputes the status from the combined set.
    """
    if existing is None:
        return addition
    violations = existing.violations + addition.violations
    warnings = existing.warnings + addition.warnings
    status = Status.FAIL if violations else (Status.WARN if warnings else Status.PASS)
    return CheckResult(
        check=addition.check, status=status, violations=violations, warnings=warnings
    )


def reanchor_results(
    *, results: list[CheckResult], from_root: Path, to_root: Path
) -> list[CheckResult]:
    """Re-express finding paths from *from_root*-relative to *to_root*-relative.

    Checks relativise findings against the root they were handed. The CLI uses
    this to move findings from a scan root to the project (config) root so config
    globs match, and the cascading runner uses it to move a nested region's
    findings up to the scan root before merging.
    """
    from_abs = from_root.resolve()
    to_abs = to_root.resolve()
    if from_abs == to_abs:
        return results

    def relocate(finding: Violation) -> Violation:
        if not finding.file:
            return finding
        try:
            moved = (from_abs / finding.file).relative_to(to_abs).as_posix()
        except ValueError:
            return finding
        return replace(finding, file=moved)

    rebuilt: list[CheckResult] = []
    for result in results:
        rebuilt.append(
            CheckResult(
                check=result.check,
                status=result.status,
                violations=[relocate(v) for v in result.violations],
                warnings=[relocate(w) for w in result.warnings],
            )
        )
    return rebuilt
