"""Illustrative call-signature comments using ellipsis to document an API shape."""

from __future__ import annotations


def register(name: str, **opts) -> None:
    # Typical usage:
    # register(name, *, timeout=..., retries=..., backoff=...)
    # register("svc", timeout=30)
    pass


def map_async(fn, items, **kw):
    # Signature: map_async(fn, items, *, workers=..., chunk_size=...)
    # Equivalent to: [fn(x) for x in items]  but parallel
    # callback signature: on_done(item, result, ...)
    return [fn(x) for x in items]


# Public surface:
#   client.get(url, *, params=..., headers=..., timeout=...)
#   client.post(url, *, json=..., data=..., headers=...)
#   client.stream(url, *, chunk_size=...)
