# why: negative - two settings loaders differ by attribute names, numeric defaults, coercion calls and key count; the differences survive string/name normalisation and represent genuinely distinct config sets.
from __future__ import annotations

import os


def load_database_settings():
    cfg = {}
    cfg["host"] = os.environ.get("DB_HOST", "localhost")
    cfg["port"] = int(os.environ.get("DB_PORT", "5432"))
    cfg["pool_size"] = int(os.environ.get("DB_POOL", "10"))
    cfg["ssl"] = os.environ.get("DB_SSL", "0") == "1"
    cfg["timeout"] = float(os.environ.get("DB_TIMEOUT", "30.0"))
    return cfg


def load_redis_settings():
    cfg = {}
    cfg["host"] = os.environ.get("REDIS_HOST", "127.0.0.1")
    cfg["port"] = int(os.environ.get("REDIS_PORT", "6379"))
    cfg["db"] = int(os.environ.get("REDIS_DB", "0"))
    return cfg
