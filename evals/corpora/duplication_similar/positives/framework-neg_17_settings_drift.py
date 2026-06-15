# why: positive - two settings loaders are the same read-coerce-validate routine copy-pasted with one numeric default changed and a single extra guard; the shared body should be a parametrised helper.
from __future__ import annotations

import os


def load_primary_cache():
    raw_host = os.environ.get("CACHE_HOST", "localhost")
    raw_port = os.environ.get("CACHE_PORT")
    port = int(raw_port) if raw_port else 6379
    if port <= 0:
        raise ValueError("bad port")
    pool = int(os.environ.get("CACHE_POOL", "10"))
    return {"host": raw_host, "port": port, "pool": pool}


def load_replica_cache():
    raw_host = os.environ.get("REPLICA_HOST", "localhost")
    raw_port = os.environ.get("REPLICA_PORT")
    port = int(raw_port) if raw_port else 6380
    if port <= 0:
        raise ValueError("bad port")
    if port > 70000:
        raise ValueError("port out of range")
    pool = int(os.environ.get("REPLICA_POOL", "10"))
    return {"host": raw_host, "port": port, "pool": pool}
