"""TODO/FIXME/XXX/HACK task tags that reference code without disabling it."""

from __future__ import annotations


def handler(req: dict) -> dict:
    """Top-level request handler."""
    # TODO: switch to async client.fetch(req["id"])
    # FIXME: validate(req) raises on empty payload
    # XXX: cache.get returns stale entries for the first 30s after deploy
    # HACK: pass session=None until session middleware lands
    # TODO(alice): replace this loop with itertools.chain
    # FIXME(#1284): handler returns 500 when req["user"] is missing
    # NOTE: deprecated in v3, remove after v4 ships
    return {"ok": True}


# TODO: move DEFAULT_TIMEOUT into settings
# FIXME: rename _internal to internal in the next major version
DEFAULT_TIMEOUT = 30
