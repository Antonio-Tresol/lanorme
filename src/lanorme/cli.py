"""Command-line entry point for LaNorme.

    lanorme check [PATHS...] [--check NAME|CODE] [--select ...] [--ignore ...]
                  [--exclude ...] [--output-format {concise,full,json,ndjson,github}]
                  [--json] [--plugin MODULE]
    lanorme rules
    lanorme rule CODE
    lanorme --version

Configuration is discovered by walking up from the target path: a dedicated
``lanorme.toml`` takes precedence, otherwise a ``[tool.lanorme]`` table in
``pyproject.toml``. CLI flags override config.
"""

from __future__ import annotations

import argparse
import fnmatch
import importlib
import os
import pkgutil
import re
import sys
import tomllib
from importlib.metadata import entry_points
from importlib.resources import files as resource_files
from pathlib import Path

import lanorme.checks
from lanorme import reporting
from lanorme import (
    Check,
    CheckResult,
    Configurable,
    Status,
    Violation,
    __version__,
    get_all_checks,
    get_check,
    run_all,
    run_check,
)
from lanorme.discovery import set_excludes
from lanorme.filtering import (
    _apply_noqa,
    _apply_promotions,
    _category,
    _keep,
    _matches,
    _rule_code,
)
from lanorme.regions import (
    Region,
    child_exclude_globs,
    combine_results,
    discover_regions,
    is_tree_scoped,
    merge_config,
    reanchor_results,
    restore_defaults,
    snapshot_defaults,
)

# Top-level ``source_root`` is injected into these two layout-aware checks only;
# every other check scans the full target tree.
_SOURCE_ROOT_CHECKS = frozenset({"layer_deps", "port_coverage"})


# --------------------------------------------------------------------------- #
# Check discovery
# --------------------------------------------------------------------------- #


def _load_builtin_checks() -> None:
    """Import every module under ``lanorme.checks`` so they self-register."""
    for mod in pkgutil.iter_modules(lanorme.checks.__path__, prefix="lanorme.checks."):
        importlib.import_module(mod.name)


def _load_entry_point_checks() -> None:
    """Import plugin modules advertised under the ``lanorme.checks`` group."""
    for ep in entry_points(group="lanorme.checks"):
        importlib.import_module(ep.value.split(":")[0])


def _load_plugin_modules(modules: list[str]) -> None:
    """Import explicitly-named plugin modules so they self-register."""
    for module in modules:
        importlib.import_module(module)


def _apply_check_config(*, config: dict[str, object]) -> None:
    """Pass each ``[tool.lanorme.<check>]`` sub-table to that check's configure().

    The top-level ``source_root`` is merged into the settings of the two
    layout-aware checks (``layer_deps`` / ``port_coverage``) so a single
    ``lanorme check .`` from the repo root can classify layers under a nested
    package directory while every other check keeps scanning the whole tree.
    """
    source_root = config.get("source_root")
    for name, check in get_all_checks().items():
        if not isinstance(check, Configurable):
            continue
        section = config.get(name)
        settings = dict(section) if isinstance(section, dict) else {}
        if (
            name in _SOURCE_ROOT_CHECKS
            and isinstance(source_root, str)
            and source_root
            and "source_root" not in settings
        ):
            settings["source_root"] = source_root
        if settings:
            check.configure(settings=settings)


# --------------------------------------------------------------------------- #
# Configuration discovery
# --------------------------------------------------------------------------- #


def _discover_config(*, start: Path) -> tuple[dict, Path, str | None]:
    """Walk up from *start* for lanorme config. Return (config, project_root, source)."""
    start = start.resolve()
    search_dir = start if start.is_dir() else start.parent
    for directory in (search_dir, *search_dir.parents):
        dedicated = directory / "lanorme.toml"
        if dedicated.is_file():
            with dedicated.open("rb") as fh:
                return tomllib.load(fh), directory, str(dedicated)

        pyproject = directory / "pyproject.toml"
        if pyproject.is_file():
            with pyproject.open("rb") as fh:
                data = tomllib.load(fh)
            tool_cfg = data.get("tool", {}).get("lanorme")
            if tool_cfg is not None:
                return tool_cfg, directory, f"{pyproject} [tool.lanorme]"

    return {}, search_dir, None


# --------------------------------------------------------------------------- #
# Profiles (``extends``)
# --------------------------------------------------------------------------- #


def _bundled_profiles() -> list[str]:
    """Names of the profiles shipped inside the package."""
    directory = resource_files("lanorme") / "profiles"
    return sorted(p.name[: -len(".toml")] for p in directory.iterdir() if p.name.endswith(".toml"))


def _load_profile(*, name: str, project_root: Path) -> dict[str, object]:
    """Load one ``extends`` entry: a local ``.toml`` path or a bundled profile name."""
    if name.endswith(".toml") or "/" in name or os.sep in name:
        path = (project_root / name).resolve()
        if not path.is_file():
            print(f"ERROR: profile file '{name}' does not exist.", file=sys.stderr)
            sys.exit(2)
        with path.open("rb") as fh:
            return tomllib.load(fh)

    resource = resource_files("lanorme") / "profiles" / f"{name}.toml"
    if not resource.is_file():
        available = ", ".join(_bundled_profiles()) or "(none)"
        print(
            f"ERROR: unknown profile '{name}'. Bundled profiles: {available}.\n"
            f"  Use a name, or a path to a .toml file.",
            file=sys.stderr,
        )
        sys.exit(2)
    return tomllib.loads(resource.read_text(encoding="utf-8"))


def _resolve_extends(*, config: dict[str, object], project_root: Path) -> dict[str, object]:
    """Expand a top-level ``extends`` into a merged base, with local keys winning.

    ``extends`` is a profile name (or list) or a path to a ``.toml`` file. Profiles
    are merged left to right, then the file's own keys are merged on top, so the
    local config always overrides what a profile sets. Profiles are flat: an
    ``extends`` inside a profile is ignored.
    """
    raw = config.get("extends")
    if not raw:
        return config
    names = [raw] if isinstance(raw, str) else list(raw)

    base: dict[str, object] = {}
    for name in names:
        profile = _load_profile(name=str(name), project_root=project_root)
        profile.pop("extends", None)
        base = merge_config(base=base, override=profile)

    local = {k: v for k, v in config.items() if k != "extends"}
    return merge_config(base=base, override=local)


# --------------------------------------------------------------------------- #
# Rule-code filtering (select / ignore)
# --------------------------------------------------------------------------- #


def _checks_for_selector(*, selector: str) -> list[Check]:
    """Return the checks that own a rule whose code or category matches *selector*."""
    wanted = selector.upper()
    matched: list[Check] = []
    for check in get_all_checks().values():
        for rule in check.rules:
            code = _rule_code(rule)
            if code == wanted or _category(code) == wanted:
                matched.append(check)
                break
    return sorted(matched, key=lambda c: c.name)


def _resolve_single(*, selector: str, src_root: str) -> tuple[list[CheckResult], list[str]]:
    """Run the check(s) named or coded by *selector*.

    Resolution is name-first (an exact check name like ``duplication``), then by
    rule code or category (``DRY-001`` / ``SIZE``, case-insensitive). When a code
    or category is given, it is returned as an implicit selector so the output is
    narrowed to that code, and only the owning check(s) run. Exits 2 if unknown.
    """
    by_name = get_check(selector)
    if by_name is not None:
        return [run_check(by_name, src_root=src_root)], []

    matched = _checks_for_selector(selector=selector)
    if matched:
        return [run_check(check, src_root=src_root) for check in matched], [selector.upper()]

    names = ", ".join(sorted(get_all_checks())) or "(none)"
    print(
        f"ERROR: '{selector}' is not a known check name, rule code, or category.\n"
        f"  Checks: {names}\n"
        f"  Run 'lanorme rules' to see every rule code and category.",
        file=sys.stderr,
    )
    sys.exit(2)


def _apply_filters(
    *,
    results: list[CheckResult],
    select: list[str],
    ignore: list[str],
) -> list[CheckResult]:
    """Drop violations/warnings whose rule code is deselected, recompute status."""
    if not select and not ignore:
        return results

    filtered: list[CheckResult] = []
    for result in results:
        violations = [v for v in result.violations if _keep(rule=v.rule, select=select, ignore=ignore)]
        warnings = [w for w in result.warnings if _keep(rule=w.rule, select=select, ignore=ignore)]
        status = Status.FAIL if violations else (Status.WARN if warnings else Status.PASS)
        filtered.append(
            CheckResult(
                check=result.check,
                status=status,
                violations=violations,
                warnings=warnings,
            )
        )
    return filtered


def _resolve_targets(paths: list[str]) -> tuple[Path, list[Path] | None]:
    """Resolve the CLI path arguments to ``(scan_root, targets)``.

    *scan_root* is the directory checks walk and relativise findings against.
    *targets* is the requested files/dirs used to narrow findings, or ``None``
    for a single directory (the whole tree is reported, exactly as before).

    Behind issue #17: ``os.walk`` over a file yields nothing, so a file target
    made every tree-walking check silently find zero. Instead we walk the file's
    directory (the scope ``lanorme check <dir>`` already uses) then post-filter.
    """
    resolved = [Path(p) for p in paths]
    for path in resolved:
        if not path.exists():
            print(f"ERROR: path '{path}' does not exist.", file=sys.stderr)
            sys.exit(2)

    if len(resolved) == 1 and resolved[0].is_dir():
        return resolved[0], None

    try:
        common = Path(os.path.commonpath([str(p.resolve()) for p in resolved]))
    except ValueError:
        print("ERROR: cannot check paths located on different drives.", file=sys.stderr)
        sys.exit(2)
    return (common.parent if common.is_file() else common), resolved


def _apply_target_filter(
    *, results: list[CheckResult], scan_root: Path, targets: list[Path] | None
) -> list[CheckResult]:
    """Keep only findings for the explicitly requested files/dirs.

    The tree under *scan_root* is walked in full so cross-file checks see the
    file's directory (the scope a directory target already gives them); this
    narrows output to the requested paths so a file target reports that file
    alone. ``None`` (a lone directory request) keeps everything.
    """
    if not targets:
        return results

    files = {t.resolve() for t in targets if t.is_file()}
    dirs = {t.resolve() for t in targets if t.is_dir()}

    def should_keep(finding: Violation) -> bool:
        absolute = (scan_root / finding.file).resolve()
        return absolute in files or any(absolute == d or d in absolute.parents for d in dirs)

    filtered: list[CheckResult] = []
    for result in results:
        violations = [v for v in result.violations if should_keep(v)]
        warnings = [w for w in result.warnings if should_keep(w)]
        status = Status.FAIL if violations else (Status.WARN if warnings else Status.PASS)
        filtered.append(
            CheckResult(check=result.check, status=status, violations=violations, warnings=warnings)
        )
    return filtered


def _path_excluded(*, path: str, patterns: list[str]) -> bool:
    normalised = path.replace("\\", "/")
    return any(fnmatch.fnmatch(normalised, pattern) for pattern in patterns)


def _apply_excludes(*, results: list[CheckResult], exclude: list[str]) -> list[CheckResult]:
    """Drop violations/warnings whose file path matches an exclude glob."""
    if not exclude:
        return results

    filtered: list[CheckResult] = []
    for result in results:
        violations = [v for v in result.violations if not _path_excluded(path=v.file, patterns=exclude)]
        warnings = [w for w in result.warnings if not _path_excluded(path=w.file, patterns=exclude)]
        status = Status.FAIL if violations else (Status.WARN if warnings else Status.PASS)
        filtered.append(
            CheckResult(
                check=result.check,
                status=status,
                violations=violations,
                warnings=warnings,
            )
        )
    return filtered


def _per_file_silences(
    *, file: str, rule: str, table: dict[str, list[str]]
) -> bool:
    """True if *rule* (full code or category) is silenced for *file* by *table*."""
    code = _rule_code(rule)
    normalised = file.replace("\\", "/")
    for pattern, codes in table.items():
        if not fnmatch.fnmatch(normalised, pattern):
            continue
        if _matches(code=code, patterns=codes):
            return True
    return False


def _apply_per_file_ignores(
    *,
    results: list[CheckResult],
    table: dict[str, list[str]],
) -> list[CheckResult]:
    """Drop violations whose ``(file, rule)`` pair is silenced by the per-file-ignores table."""
    if not table:
        return results

    filtered: list[CheckResult] = []
    for result in results:
        violations = [
            v for v in result.violations
            if not _per_file_silences(file=v.file, rule=v.rule, table=table)
        ]
        warnings = [
            w for w in result.warnings
            if not _per_file_silences(file=w.file, rule=w.rule, table=table)
        ]
        status = Status.FAIL if violations else (Status.WARN if warnings else Status.PASS)
        filtered.append(
            CheckResult(
                check=result.check,
                status=status,
                violations=violations,
                warnings=warnings,
            )
        )
    return filtered


# --------------------------------------------------------------------------- #
# Output helpers
# --------------------------------------------------------------------------- #


def _csv(value: str | None) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()] if value else []


def _config_list(value: object) -> list[str]:
    """Normalise a config selector value to a list of strings.

    Accepts a list (``promote = ["TYPE-004"]``) or a bare string
    (``promote = "ALL"``); anything else yields ``[]``. Whitespace and case are
    handled downstream by ``_matches``, matching the CLI ``_csv`` path.
    """
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [str(item) for item in value]
    return []


def _parse_per_file_ignores(*, table: object) -> dict[str, list[str]]:
    """Normalise the ``[tool.lanorme.per-file-ignores]`` TOML table to {glob: [codes]}."""
    if not isinstance(table, dict):
        return {}
    out: dict[str, list[str]] = {}
    for pattern, codes in table.items():
        if not isinstance(pattern, str) or not isinstance(codes, list):
            continue
        normalised = [c for c in codes if isinstance(c, str)]
        if normalised:
            out[pattern] = normalised
    return out


# --------------------------------------------------------------------------- #
# Argument parsing
# --------------------------------------------------------------------------- #


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="lanorme",
        description="La norme — architecture & code-quality linter for Python.",
    )
    parser.add_argument("--version", action="version", version=f"lanorme {__version__}")
    sub = parser.add_subparsers(dest="command")

    check = sub.add_parser("check", help="Run checks against one or more paths.")
    check.add_argument("paths", nargs="*", default=["."], help="Path(s) to check (default: .)")
    check.add_argument(
        "--check",
        dest="single",
        default=None,
        help="Run a single check by name (e.g. duplication), or by rule code/category (e.g. DRY-001, SIZE).",
    )
    check.add_argument("--select", default=None, help="Comma-separated rule codes/categories to run.")
    check.add_argument("--ignore", default=None, help="Comma-separated rule codes/categories to skip.")
    check.add_argument("--exclude", default=None, help="Comma-separated file-path globs to exclude.")
    check.add_argument(
        "--promote",
        default=None,
        help="Comma-separated rule codes/categories whose warnings become build-failing errors (or ALL).",
    )
    check.add_argument(
        "--show-config",
        action="store_true",
        help="Print the discovered config and effective per-check settings, then exit.",
    )
    check.add_argument("--plugin", action="append", default=[], help="Plugin module to load (repeatable).")
    check.add_argument(
        "--output-format",
        choices=["concise", "full", "json", "ndjson", "github"],
        default=None,
        help=(
            "Output format (default: concise). 'concise' shows only checks with findings plus a "
            "summary; 'full' shows every check; 'json' is one object per check; 'ndjson' is one "
            "finding per line; 'github' emits workflow commands (auto-detected when GITHUB_ACTIONS=true)."
        ),
    )
    check.add_argument("--json", action="store_true", help="Alias for --output-format=json.")

    sub.add_parser("rules", help="List all registered rules and exit.")

    rule = sub.add_parser("rule", help="Print the reference section for a single rule code.")
    rule.add_argument("code", help="The rule code to look up (e.g. CMT-001, SQL-001).")

    return parser


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #


def _run_regions(
    *,
    regions: list[Region],
    root_config: dict[str, object],
    scan_root: Path,
    exclude: list[str],
    pristine: dict[str, object],
) -> list[CheckResult]:
    """Run the checks under cascading per-directory config and merge the results.

    File-level checks run once per region, each pass scoped to the files that
    region directly governs (the nested regions below it are excluded) and
    configured with that region's merged settings; their findings are re-anchored
    back to the scan root and folded together. Whole-tree checks run once at the
    scan root under the root config. Results land in scan-root coordinates, the
    same as a single-region run, so the downstream pipeline is unchanged.
    """
    checks = get_all_checks()
    by_name: dict[str, CheckResult] = {}

    restore_defaults(checks=checks, snapshot=pristine)
    _apply_check_config(config=root_config)
    set_excludes(exclude)
    for name, check in checks.items():
        if is_tree_scoped(check):
            by_name[name] = run_check(check, src_root=str(scan_root))

    root_dir = scan_root.resolve()
    for region in regions:
        restore_defaults(checks=checks, snapshot=pristine)
        _apply_check_config(config=region.merged)
        region_excludes = child_exclude_globs(region=region, regions=regions)
        # The user's excludes are written relative to the scan root, so they
        # prune correctly only in the root region's walk (rooted there). Nested
        # regions walk from their own directory, where those globs would not
        # line up, so their user excludes are left to the post-filter, which
        # works in project-root coordinates and still drops the findings.
        if region.directory == root_dir:
            region_excludes = list(exclude) + region_excludes
        set_excludes(region_excludes)
        for name, check in checks.items():
            if is_tree_scoped(check):
                continue
            result = run_check(check, src_root=str(region.directory))
            (result,) = reanchor_results(
                results=[result], from_root=region.directory, to_root=scan_root
            )
            by_name[name] = combine_results(existing=by_name.get(name), addition=result)

    return [by_name[name] for name in checks if name in by_name]


def _run_and_report(
    *,
    args: argparse.Namespace,
    config: dict[str, object],
    scan_root: Path,
    project_root: Path,
    targets: list[Path] | None,
    pristine: dict[str, object],
) -> None:
    """Run the selected checks, apply the filters, print, and set the exit code."""
    src_root = str(scan_root)
    ignore = _csv(args.ignore) or _config_list(config.get("ignore"))
    exclude = _csv(args.exclude) or _config_list(config.get("exclude"))
    promote = _csv(args.promote) or _config_list(config.get("promote"))
    per_file_ignores = _parse_per_file_ignores(table=config.get("per-file-ignores", {}))
    output_format = reporting.resolve_output_format(explicit=args.output_format, as_json=args.json)

    # Publish excludes so checks prune them (plus the built-in junk dirs) at
    # walk time, not just in the post-filter below. Always set, even to (), so
    # a previous in-process run's value does not leak.
    set_excludes(exclude)

    if args.single:
        results, implicit_select = _resolve_single(selector=args.single, src_root=src_root)
    else:
        implicit_select = []
        regions = discover_regions(scan_root=scan_root, root_config=config)
        if len(regions) == 1:
            results = run_all(src_root=src_root)
        else:
            results = _run_regions(
                regions=regions,
                root_config=config,
                scan_root=scan_root,
                exclude=exclude,
                pristine=pristine,
            )

    if not results:
        print("No checks registered.")
        return

    # A code-form ``--check`` (e.g. DRY-001) narrows output to that code; an
    # explicit ``--select`` is otherwise honoured, then config ``select``.
    select = implicit_select or _csv(args.select) or _config_list(config.get("select"))

    # When the request is narrower than the walked tree (a file, or a subset of
    # paths), keep only findings for the requested targets. A lone directory
    # request passes ``targets=None`` and this is a no-op.
    results = _apply_target_filter(results=results, scan_root=scan_root, targets=targets)
    # The target filter works in scan-root-relative paths; everything after it
    # (config globs, noqa source lookup, display) works in project-root-relative.
    results = reanchor_results(results=results, from_root=scan_root, to_root=project_root)
    results = _apply_filters(results=results, select=select, ignore=ignore)
    results = _apply_excludes(results=results, exclude=exclude)
    results = _apply_per_file_ignores(results=results, table=per_file_ignores)
    results = _apply_noqa(results=results, project_root=project_root)
    results = _apply_promotions(results=results, promote=promote)
    reporting.emit(results=results, output_format=output_format)

    if any(r.status == Status.FAIL for r in results):
        sys.exit(1)


def _command_check(*, args: argparse.Namespace) -> None:
    """Handle the ``check`` subcommand: discover config, then report or run."""
    scan_root, targets = _resolve_targets(args.paths)

    config, project_root, config_source = _discover_config(start=scan_root)
    config = _resolve_extends(config=config, project_root=project_root)
    _load_plugin_modules([*config.get("plugins", []), *args.plugin])
    # Capture pristine defaults, then reset every check to them before applying
    # config. configure() only ever sets, never resets, so without this a check
    # configured by an earlier invocation in the same process would leak its
    # settings into this run. The cascading runner reuses the snapshot to reset
    # between regions.
    checks = get_all_checks()
    pristine = snapshot_defaults(checks)
    restore_defaults(checks=checks, snapshot=pristine)
    _apply_check_config(config=config)

    if args.show_config:
        reporting.print_config(config=config, source=config_source, project_root=project_root)
        return

    _run_and_report(
        args=args,
        config=config,
        scan_root=scan_root,
        project_root=project_root,
        targets=targets,
        pristine=pristine,
    )


def main(argv: list[str] | None = None) -> None:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help()
        sys.exit(2)

    # `rules` needs the registry but no target.
    _load_builtin_checks()
    _load_entry_point_checks()

    if args.command == "rules":
        reporting.print_rules()
        return

    if args.command == "rule":
        sys.exit(reporting.print_rule_detail(code=args.code))

    _command_check(args=args)


if __name__ == "__main__":
    main()
