"""Command-line entry point for LaNorme.

    lanorme check [PATHS...] [--check NAME] [--select ...] [--ignore ...]
                  [--output-format {full,json}] [--plugin MODULE]
    lanorme rules
    lanorme --version

Configuration is discovered by walking up from the target path: a dedicated
``lanorme.toml`` takes precedence, otherwise a ``[tool.lanorme]`` table in
``pyproject.toml``. CLI flags override config.
"""

from __future__ import annotations

import argparse
import fnmatch
import importlib
import json
import pkgutil
import re
import sys
import tomllib
from importlib.metadata import entry_points
from pathlib import Path

import lanorme.checks
from lanorme import (
    CheckResult,
    Status,
    __version__,
    get_all_checks,
    get_check,
    run_all,
)

_CODE_RE = re.compile(r"^([A-Z]+)-\d+")


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
    """Pass each ``[tool.lanorme.<check>]`` sub-table to that check's configure()."""
    for name, check in get_all_checks().items():
        section = config.get(name)
        if isinstance(section, dict) and hasattr(check, "configure"):
            check.configure(settings=section)


# --------------------------------------------------------------------------- #
# Configuration discovery
# --------------------------------------------------------------------------- #


def _discover_config(*, start: Path) -> tuple[dict, Path]:
    """Walk up from *start* looking for lanorme config. Return (config, project_root)."""
    start = start.resolve()
    search_dir = start if start.is_dir() else start.parent
    for directory in (search_dir, *search_dir.parents):
        dedicated = directory / "lanorme.toml"
        if dedicated.is_file():
            with dedicated.open("rb") as fh:
                return tomllib.load(fh), directory

        pyproject = directory / "pyproject.toml"
        if pyproject.is_file():
            with pyproject.open("rb") as fh:
                data = tomllib.load(fh)
            tool_cfg = data.get("tool", {}).get("lanorme")
            if tool_cfg is not None:
                return tool_cfg, directory

    return {}, search_dir


# --------------------------------------------------------------------------- #
# Rule-code filtering (select / ignore)
# --------------------------------------------------------------------------- #


def _rule_code(rule: str) -> str:
    """Extract the rule code (e.g. 'LAYER-002') from a rule string."""
    return rule.split(":", 1)[0].strip().split()[0]


def _category(code: str) -> str:
    """The category prefix of a code, e.g. 'LAYER' from 'LAYER-002'."""
    match = _CODE_RE.match(code)
    return match.group(1) if match else code


def _matches(*, code: str, patterns: list[str]) -> bool:
    """True if *code* matches any selector (exact code, category, or 'ALL')."""
    category = _category(code)
    return any(p == "ALL" or p == code or p == category for p in patterns)


def _keep(*, rule: str, select: list[str], ignore: list[str]) -> bool:
    code = _rule_code(rule)
    selected = not select or _matches(code=code, patterns=select)
    return selected and not _matches(code=code, patterns=ignore)


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


# --------------------------------------------------------------------------- #
# Output
# --------------------------------------------------------------------------- #


def _print_results(*, results: list[CheckResult], json_output: bool) -> None:
    if json_output:
        print(json.dumps([r.to_dict() for r in results], indent=2))
        return
    for result in results:
        print(result.format_human())
        print()


def _print_rules() -> None:
    checks = get_all_checks()
    if not checks:
        print("No checks registered.")
        return
    for check in sorted(checks.values(), key=lambda c: c.name):
        print(f"\n## {check.name} — {check.description}")
        for rule in check.rules:
            print(f"  {rule}")


def _csv(value: str | None) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()] if value else []


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
    check.add_argument("--check", dest="single", default=None, help="Run a single check by name.")
    check.add_argument("--select", default=None, help="Comma-separated rule codes/categories to run.")
    check.add_argument("--ignore", default=None, help="Comma-separated rule codes/categories to skip.")
    check.add_argument("--exclude", default=None, help="Comma-separated file-path globs to exclude.")
    check.add_argument("--plugin", action="append", default=[], help="Plugin module to load (repeatable).")
    check.add_argument(
        "--output-format",
        choices=["full", "json"],
        default="full",
        help="Output format (default: full).",
    )
    check.add_argument("--json", action="store_true", help="Alias for --output-format=json.")

    sub.add_parser("rules", help="List all registered rules and exit.")
    return parser


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #


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
        _print_rules()
        return

    # command == "check"
    target = Path(args.paths[0])
    if not target.exists():
        print(f"ERROR: path '{target}' does not exist.", file=sys.stderr)
        sys.exit(2)

    config, _project_root = _discover_config(start=target)
    _load_plugin_modules([*config.get("plugins", []), *args.plugin])
    _apply_check_config(config=config)

    select = _csv(args.select) or list(config.get("select", []))
    ignore = _csv(args.ignore) or list(config.get("ignore", []))
    exclude = _csv(args.exclude) or list(config.get("exclude", []))
    json_output = args.json or args.output_format == "json"

    src_root = str(target)
    if args.single:
        check = get_check(args.single)
        if check is None:
            available = ", ".join(sorted(get_all_checks())) or "(none)"
            print(f"ERROR: Unknown check '{args.single}'. Available: {available}", file=sys.stderr)
            sys.exit(2)
        results = [check.run(src_root=src_root)]
    else:
        results = run_all(src_root=src_root)

    if not results:
        print("No checks registered.")
        return

    results = _apply_filters(results=results, select=select, ignore=ignore)
    results = _apply_excludes(results=results, exclude=exclude)
    _print_results(results=results, json_output=json_output)

    if any(r.status == Status.FAIL for r in results):
        sys.exit(1)


if __name__ == "__main__":
    main()
