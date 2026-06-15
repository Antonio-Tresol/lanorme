# why: negative - parallel shape but one RAISES on a missing key while the other returns a default and continues; divergent error contract, must not merge.
from __future__ import annotations


def require_setting(config, keys):
    resolved = {}
    missing = []
    for key in keys:
        if key not in config:
            raise KeyError(f"missing {key}")
        resolved[key] = config[key]
    if not resolved:
        raise ValueError("no keys")
    return resolved


def lenient_setting(config, keys):
    resolved = {}
    missing = []
    for key in keys:
        if key not in config:
            missing.append(key)
            resolved[key] = None
            continue
        resolved[key] = config[key]
    if not resolved:
        return {}
    return resolved
