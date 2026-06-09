"""Config profiles for ``extends``: bundled presets and local ``.toml`` files.

``[tool.lanorme] extends = ["strict", "hexagonal"]`` adopts one or more profiles
(shipped under ``lanorme/profiles/*.toml``, or a path to a local file). They are
merged left to right and the project's own config is merged on top, so local
keys always win. This module only resolves config dicts; it has no
argument-parsing concern, so both the CLI (root config) and the cascading region
loader can call it.
"""

from __future__ import annotations

import os
import sys
import tomllib
from importlib.resources import files as resource_files
from pathlib import Path

from lanorme.regions import merge_config


def _bundled_profiles() -> list[str]:
    """Names of the profiles shipped inside the package."""
    directory = resource_files("lanorme") / "profiles"
    return sorted(p.name[: -len(".toml")] for p in directory.iterdir() if p.name.endswith(".toml"))


def _parse_profile_toml(*, text: str, label: str) -> dict[str, object]:
    """Parse a profile's TOML, exiting cleanly (not with a traceback) if malformed."""
    try:
        return tomllib.loads(text)
    except tomllib.TOMLDecodeError as error:
        print(f"ERROR: profile '{label}' is not valid TOML: {error}", file=sys.stderr)
        sys.exit(2)


def _load_profile(*, name: str, project_root: Path) -> dict[str, object]:
    """Load one ``extends`` entry: a local ``.toml`` path or a bundled profile name."""
    if name.endswith(".toml") or "/" in name or os.sep in name:
        path = (project_root / name).resolve()
        if not path.is_file():
            print(f"ERROR: profile file '{name}' does not exist.", file=sys.stderr)
            sys.exit(2)
        return _parse_profile_toml(text=path.read_text(encoding="utf-8"), label=name)

    resource = resource_files("lanorme") / "profiles" / f"{name}.toml"
    if not resource.is_file():
        available = ", ".join(_bundled_profiles()) or "(none)"
        print(
            f"ERROR: unknown profile '{name}'. Bundled profiles: {available}.\n"
            f"  Use a name, or a path to a .toml file.",
            file=sys.stderr,
        )
        sys.exit(2)
    return _parse_profile_toml(text=resource.read_text(encoding="utf-8"), label=name)


def _resolve_extends(*, config: dict[str, object], project_root: Path) -> dict[str, object]:
    """Expand a top-level ``extends`` into a merged base, with local keys winning.

    ``extends`` is a profile name (or list) or a path to a ``.toml`` file. Profiles
    are merged left to right, then the config's own keys are merged on top, so the
    local config always overrides what a profile sets. Profiles are flat: an
    ``extends`` inside a profile is ignored.
    """
    raw = config.get("extends")
    if not raw:
        return config
    if isinstance(raw, str):
        names = [raw]
    elif isinstance(raw, list) and all(isinstance(entry, str) for entry in raw):
        names = raw
    else:
        print(
            "ERROR: 'extends' must be a profile name or a list of names/paths "
            f"(got {type(raw).__name__}).",
            file=sys.stderr,
        )
        sys.exit(2)

    base: dict[str, object] = {}
    for name in names:
        profile = _load_profile(name=str(name), project_root=project_root)
        profile.pop("extends", None)
        base = merge_config(base=base, override=profile)

    local = {k: v for k, v in config.items() if k != "extends"}
    return merge_config(base=base, override=local)
