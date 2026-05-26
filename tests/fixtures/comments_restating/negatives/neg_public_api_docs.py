"""Public-API usage notes and examples: documentation that earns its keep."""

from __future__ import annotations


def connect(dsn: str, *, pool_size: int = 5):
    # Example: connect("postgres://localhost/db", pool_size=20)
    return {"dsn": dsn, "pool_size": pool_size}


def parse_duration(text: str) -> int:
    # Accepts "10s", "5m", "2h"; returns the total in seconds.
    units = {"s": 1, "m": 60, "h": 3600}
    return int(text[:-1]) * units[text[-1]]


def register(name: str, handler) -> None:
    # Handlers are called in registration order; later wins on conflict.
    _registry[name] = handler


def paginate(items: list[int], size: int):
    # Yields lists of at most `size`; the final page may be shorter.
    for start in range(0, len(items), size):
        yield items[start : start + size]


def deprecated_alias(x):
    # Deprecated since 2.0: use compute() instead; removed in 3.0.
    return x


_registry: dict = {}
