# why: negative - parallel config/dict builders. The shape repeats but the keys
# why: and attribute names ARE the payload; there is no shared algorithm to
# why: extract, so flagging this would be a false positive against boilerplate.
"""Two settings builders where the field names carry the whole meaning."""

from __future__ import annotations


def build_db_config(env):
    config = {}
    config["host"] = env.get("DB_HOST", "localhost")
    config["port"] = int(env.get("DB_PORT", "5432"))
    config["user"] = env.get("DB_USER", "postgres")
    config["sslmode"] = env.get("DB_SSL", "require")
    return config


def build_cache_config(env):
    config = {}
    config["host"] = env.get("REDIS_HOST", "localhost")
    config["port"] = int(env.get("REDIS_PORT", "6379"))
    if env.get("REDIS_PASS"):
        config["password"] = env["REDIS_PASS"]
    config["db_index"] = int(env.get("REDIS_DB", "0"))
    return config
