"""Type annotations and function-parameter defaults — not assignments of secrets."""

from __future__ import annotations


password: str
api_key: str
secret_key: bytes
token: str | None


def login(*, user: str, password: str = "") -> None:
    """Log in with the given password."""
    _ = (user, password)


def connect(*, host: str, password: str | None = None) -> None:
    _ = (host, password)


def make_token(*, secret: str = "", expiry: int = 3600) -> str:
    return f"{secret}:{expiry}"


def request(*, url: str, bearer_token: str | None = None) -> None:
    _ = (url, bearer_token)


class Credentials:
    password: str
    api_key: str
    secret_key: str
    token: str | None
