# why: negative - one loader reads from the environment and another parses a file; they share the goal of producing a config dict but use different sources, parsing and control flow.
from __future__ import annotations

import json
import os


def load_from_env():
    cfg = {}
    cfg["region"] = os.environ.get("APP_REGION", "eu-west-1")
    cfg["workers"] = int(os.environ.get("APP_WORKERS", "4"))
    cfg["debug"] = os.environ.get("APP_DEBUG", "false") == "true"
    cfg["retries"] = int(os.environ.get("APP_RETRIES", "3"))
    return cfg


def load_from_file(path):
    raw = open(path, encoding="utf-8").read()
    parsed = json.loads(raw)
    cfg = {}
    for key, value in parsed.items():
        normalised = key.strip().lower()
        cfg[normalised] = value
    cfg.setdefault("region", "eu-west-1")
    return cfg
