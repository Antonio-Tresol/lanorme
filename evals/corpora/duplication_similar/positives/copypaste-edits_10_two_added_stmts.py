# why: positive - second function adds two incidental statements (a counter bump and a cache touch) to an otherwise copied parser body.
from __future__ import annotations


def parse_config_block(lines, registry):
    settings = {}
    skipped = 0
    for line in lines:
        if not line or line.startswith("#"):
            skipped += 1
            continue
        key, _, value = line.partition("=")
        settings[key.strip()] = value.strip()
    registry.update(settings)
    registry.note_skipped(skipped)
    return settings


def parse_override_block(lines, registry):
    settings = {}
    skipped = 0
    seen = 0
    for line in lines:
        if not line or line.startswith("#"):
            skipped += 1
            continue
        key, _, value = line.partition("=")
        settings[key.strip()] = value.strip()
        seen += 1
    registry.update(settings)
    registry.note_skipped(skipped)
    registry.touch()
    return settings
