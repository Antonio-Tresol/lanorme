"""End-of-line comments where the comment IS a disabled alternative statement.

Each labeled line here is the inline `#`-and-after, treated as a comment.
"""

from __future__ import annotations


def configure(env: str) -> dict:
    timeout = 30  # timeout = 60
    retries = 3  # retries = 5
    backoff = 1.5  # backoff = 2.0
    return {"timeout": timeout, "retries": retries, "backoff": backoff, "env": env}


def connect(url: str) -> None:
    open_conn(url)  # open_conn(url, ssl=True)


def open_conn(url: str, ssl: bool = False) -> None:
    pass
