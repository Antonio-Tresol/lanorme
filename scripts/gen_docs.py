#!/usr/bin/env python3
"""Generate the agent-facing docs that must never drift from the tool.

LaNorme makes a codebase's standard executable; its docs follow the same rule.
The facts that drift -- the configuration keys, their types and defaults, the
set of rules, and which checks are opt-in -- are generated here from the tool
itself, so a stale fact fails CI rather than misleading a reader. The authored
prose (what a rule catches, why, its precision notes) lives in ``docs/`` and is
not touched by this script.

Outputs (run from the repo root):

    lanorme.schema.json            JSON Schema for ``[tool.lanorme]`` (editors, agents)
    docs/reference/configuration.md   Every top-level config key, generated
    docs/reference/rules-index.md     Code -> check -> opt-in table, generated
    llms.txt                       Curated index of the docs, for agents
    llms-full.txt                  The reference docs concatenated, for agents

Usage:

    python3 scripts/gen_docs.py            # write the generated files
    python3 scripts/gen_docs.py --check    # exit 1 if any committed file is stale
"""

from __future__ import annotations

import importlib
import json
import pkgutil
import sys
from dataclasses import dataclass
from pathlib import Path

from lanorme import get_all_checks

REPO_ROOT = Path(__file__).resolve().parents[1]
SITE_BASE = "https://lanorme.github.io/lanorme"


@dataclass(frozen=True)
class ConfigKey:
    """One top-level ``[tool.lanorme]`` key, the single source for its docs."""

    name: str
    toml_type: str
    json_schema: dict[str, object]
    default: str
    feature: str
    summary: str
    example: str


# The top-level configuration surface. Per-check tables (`[tool.lanorme.<check>]`)
# are documented per rule in docs/RULES.md; these are the cross-cutting keys.
CONFIG_KEYS: tuple[ConfigKey, ...] = (
    ConfigKey(
        name="select",
        toml_type="list of strings",
        json_schema={"type": "array", "items": {"type": "string"}},
        default="all enabled checks",
        feature="Filtering",
        summary="Run only these rule codes or categories. A category (``SEC``) covers every code in it; ``ALL`` selects everything.",
        example='select = ["SECRETPY", "TYPE-004"]',
    ),
    ConfigKey(
        name="ignore",
        toml_type="list of strings",
        json_schema={"type": "array", "items": {"type": "string"}},
        default="[] (nothing ignored)",
        feature="Filtering",
        summary="Skip these rule codes or categories everywhere.",
        example='ignore = ["NAMING-003"]',
    ),
    ConfigKey(
        name="exclude",
        toml_type="list of glob strings",
        json_schema={"type": "array", "items": {"type": "string"}},
        default="[] (built-in junk dirs only)",
        feature="Filtering",
        summary="File-path globs to skip entirely; matched files are never walked.",
        example='exclude = ["**/migrations/*", "generated/*"]',
    ),
    ConfigKey(
        name="per-file-ignores",
        toml_type="table of glob to code list",
        json_schema={
            "type": "object",
            "additionalProperties": {"type": "array", "items": {"type": "string"}},
        },
        default="{} (no per-file rules)",
        feature="Filtering",
        summary="Suppress specific rule codes or categories for files matching a glob.",
        example='[tool.lanorme.per-file-ignores]\n"tests/*" = ["SIZE-001", "AAA"]',
    ),
    ConfigKey(
        name="promote",
        toml_type="list of strings",
        json_schema={"type": "array", "items": {"type": "string"}},
        default="[] (advisories stay warnings)",
        feature="Severity",
        summary="Advisory warnings whose codes (or ``ALL``) become build-failing errors. Runs after every suppression, so an ignored or noqa'd warning is never promoted.",
        example='promote = ["TYPE-004"]   # or ["ALL"]',
    ),
    ConfigKey(
        name="extends",
        toml_type="string or list of strings",
        json_schema={
            "oneOf": [{"type": "string"}, {"type": "array", "items": {"type": "string"}}]
        },
        default="none",
        feature="Profiles",
        summary="Adopt one or more profiles -- a bundled name (``strict``, ``hexagonal``, ``clean``, ``layered``) or a path to a local ``.toml``. Profiles merge left to right, then your own keys merge on top, so local always wins.",
        example='extends = ["strict", "hexagonal"]',
    ),
    ConfigKey(
        name="baseline",
        toml_type="string (path)",
        json_schema={"type": "string"},
        default="none",
        feature="Adoption",
        summary="Path to a baseline file. Findings recorded by ``lanorme baseline write`` are suppressed, so only new findings report. See the adoption tutorial.",
        example='baseline = "lanorme-baseline.json"',
    ),
    ConfigKey(
        name="source_root",
        toml_type="string (path)",
        json_schema={"type": "string"},
        default="the scan root",
        feature="Architecture",
        summary="The top-level package directory when ports, adapters and layers live under a nested package; the architecture checks interpret their paths relative to it.",
        example='source_root = "src/myapp"',
    ),
    ConfigKey(
        name="plugins",
        toml_type="list of strings",
        json_schema={"type": "array", "items": {"type": "string"}},
        default="[] (built-in checks only)",
        feature="Extensibility",
        summary="Extra check modules to import so they self-register, beyond the built-ins and entry-point plugins.",
        example='plugins = ["my_company.lanorme_checks"]',
    ),
)


def _load_checks() -> dict[str, object]:
    """Import every built-in check so the registry is populated, then return it."""
    package = importlib.import_module("lanorme.checks")
    for module in pkgutil.iter_modules(package.__path__):
        importlib.import_module(f"lanorme.checks.{module.name}")
    return get_all_checks()


def render_schema() -> str:
    """Render the JSON Schema for ``[tool.lanorme]``."""
    properties: dict[str, object] = {}
    for key in CONFIG_KEYS:
        schema = dict(key.json_schema)
        schema["description"] = key.summary.replace("``", "`")
        properties[key.name] = schema

    # Per-check tables: each registered check may be configured under its own
    # name, always with an ``enabled`` toggle (opt-in checks default off).
    for name in sorted(_load_checks()):
        properties[name] = {
            "type": "object",
            "description": f"Settings for the {name} check (see docs/RULES.md).",
            "properties": {"enabled": {"type": "boolean"}},
        }

    schema = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "$id": f"{SITE_BASE}/lanorme.schema.json",
        "title": "LaNorme configuration",
        "description": "The [tool.lanorme] table in pyproject.toml, or top-level keys in a standalone lanorme.toml.",
        "type": "object",
        "properties": properties,
        "additionalProperties": False,
    }
    return json.dumps(schema, indent=2) + "\n"


def render_config_reference() -> str:
    """Render docs/reference/configuration.md from the config-key source."""
    lines = [
        "# Configuration reference",
        "",
        "This reference lists every top-level key in the `[tool.lanorme]` table, generated",
        "from the tool so it cannot drift. Per-check settings (`[tool.lanorme.<check>]`) are",
        "documented with each rule in the [rule reference](../RULES.md). A machine-readable",
        f"[`lanorme.schema.json`]({SITE_BASE}/lanorme.schema.json) validates this table in editors.",
        "",
        "Configuration lives in `[tool.lanorme]` in `pyproject.toml`, or in a standalone",
        "`lanorme.toml` / `.lanorme.toml`. **The table header differs between the two.** In",
        "`pyproject.toml` every key sits under `[tool.lanorme]`, and a per-check table under",
        "`[tool.lanorme.<check>]`. In a standalone `lanorme.toml` the prefix is dropped: keys",
        "are top-level (`promote = [\"TYPE-004\"]`) and a sub-table is bare (`[per-file-ignores]`,",
        "`[prose]`). The examples below show the `pyproject.toml` form; a `[tool.lanorme]` prefix",
        "written inside a `lanorme.toml` is silently ignored. Keys also have command-line",
        "equivalents (`--select`, `--ignore`); the command line wins over config.",
        "",
        "| Key | Type | Default | Feature |",
        "| --- | --- | --- | --- |",
    ]
    for key in CONFIG_KEYS:
        lines.append(f"| [`{key.name}`](#{key.name}) | {key.toml_type} | {key.default} | {key.feature} |")
    lines.append("")
    for key in CONFIG_KEYS:
        lines.extend(
            [
                f"## `{key.name}`",
                "",
                key.summary.replace("``", "`"),
                "",
                "```toml",
                key.example,
                "```",
                "",
            ]
        )
    lines.extend(
        [
            "## Per-check settings",
            "",
            "Each check is configured under its own table, always with an `enabled`",
            "toggle (opt-in checks default to `false`). The settings a check accepts are",
            "listed in its [rule reference](../RULES.md) section. For example:",
            "",
            "```toml",
            "[tool.lanorme.prose]",
            "enabled = true",
            "",
            "[tool.lanorme.layer_deps]",
            'composition_root = ["api/dependencies.py"]',
            "```",
            "",
        ]
    )
    return "\n".join(lines)


def render_rules_index() -> str:
    """Render docs/reference/rules-index.md: a code/check/opt-in table from the registry."""
    checks = _load_checks()
    lines = [
        "# Rule index",
        "",
        "This reference maps every rule code to its check and whether the check is opt-in",
        "(default off), generated from the registry. Full descriptions, configuration and precision",
        "notes for each rule are in the [rule reference](../RULES.md).",
        "",
        "| Rule | Check | Opt-in |",
        "| --- | --- | --- |",
    ]
    rows: list[tuple[str, str, str]] = []
    for name, check in checks.items():
        opt_in = "yes" if not getattr(check, "enabled", True) else "no"
        for rule in getattr(check, "rules", []):
            code = rule.split(":", 1)[0].strip()
            rows.append((code, name, opt_in))
    for code, name, opt_in in sorted(rows):
        lines.append(f"| `{code}` | {name} | {opt_in} |")
    lines.append("")
    return "\n".join(lines)


# Pages listed in llms.txt, in reading order. (path-under-docs, title, blurb).
LLMS_PAGES: tuple[tuple[str, str, str], ...] = (
    ("index.md", "Overview", "What LaNorme is and the precision-first principle."),
    ("tutorials/adopt-on-existing-codebase.md", "Tutorial: adopt on an existing codebase", "Two-command baseline onboarding for a brownfield repo."),
    ("how-to/configure-checks.md", "How-to: configure checks", "Select, ignore, exclude, per-file-ignores and noqa."),
    ("how-to/promote-warnings.md", "How-to: promote warnings to errors", "Make advisory rules build-failing."),
    ("how-to/use-profiles.md", "How-to: use profiles", "Adopt strict and the architecture presets via extends."),
    ("how-to/write-a-check.md", "How-to: write a check", "Add a custom rule as a plugin."),
    ("reference/configuration.md", "Reference: configuration", "Every [tool.lanorme] key."),
    ("RULES.md", "Reference: rules", "What every rule catches and how to configure it."),
    ("reference/rules-index.md", "Reference: rule index", "Code to check mapping."),
    ("reference/cli.md", "Reference: CLI", "Every command and flag."),
    ("explanation/precision-first.md", "Explanation: precision-first", "Why a false positive is the cardinal sin."),
)


def render_llms_txt() -> str:
    """Render llms.txt: the curated agent index (the llmstxt.org convention)."""
    lines = [
        "# LaNorme",
        "",
        "> A precision-first, standard-library-only Python linter that makes a team's",
        "> coding standard -- quality, style, architecture, structure -- executable on",
        "> every commit. A false positive (firing on correct code) is the cardinal sin.",
        "",
        "Every page below is Markdown. Append `.md` to any docs URL to get its raw",
        "Markdown, or read these source files directly. `lanorme rule <CODE>` prints a",
        "rule's reference in the terminal; `lanorme.schema.json` validates configuration.",
        "",
        "## Docs",
        "",
    ]
    for path, title, blurb in LLMS_PAGES:
        lines.append(f"- [{title}]({SITE_BASE}/{path}): {blurb}")
    lines.append("")
    return "\n".join(lines)


def render_llms_full() -> str:
    """Render llms-full.txt: the reference docs concatenated for full-context ingestion."""
    parts = [
        "# LaNorme, full reference",
        "",
        "The generated and authored reference docs concatenated for agent ingestion.",
        "",
    ]
    sources = [
        REPO_ROOT / "docs" / "reference" / "configuration.md",
        REPO_ROOT / "docs" / "reference" / "rules-index.md",
        REPO_ROOT / "docs" / "RULES.md",
    ]
    for source in sources:
        if source.is_file():
            parts.append(f"\n\n---\n\n# Source: {source.relative_to(REPO_ROOT).as_posix()}\n")
            parts.append(source.read_text(encoding="utf-8"))
    return "".join(parts)


# (relative output path, render function). Order matters: configuration and
# rules-index render before llms-full, which concatenates them.
OUTPUTS: tuple[tuple[str, object], ...] = (
    ("lanorme.schema.json", render_schema),
    ("docs/reference/configuration.md", render_config_reference),
    ("docs/reference/rules-index.md", render_rules_index),
    ("llms.txt", render_llms_txt),
    ("llms-full.txt", render_llms_full),
)


def _write_all() -> None:
    """Generate every output file."""
    for relative, render in OUTPUTS:
        path = REPO_ROOT / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(render(), encoding="utf-8")
        print(f"wrote {relative}")


def _check_all() -> int:
    """Return 1 if any committed output is stale versus a fresh render."""
    stale: list[str] = []
    for relative, render in OUTPUTS:
        path = REPO_ROOT / relative
        current = path.read_text(encoding="utf-8") if path.is_file() else ""
        if current != render():
            stale.append(relative)
    if stale:
        print("stale generated docs (run scripts/gen_docs.py):", file=sys.stderr)
        for relative in stale:
            print(f"  {relative}", file=sys.stderr)
        return 1
    print("generated docs are in sync.")
    return 0


def main(*, argv: list[str]) -> int:
    """Write the generated docs, or with --check verify they are in sync."""
    if "--check" in argv:
        return _check_all()
    _write_all()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(argv=sys.argv[1:]))
