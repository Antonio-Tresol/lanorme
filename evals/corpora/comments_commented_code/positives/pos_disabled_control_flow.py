"""Disabled control-flow statements: if/for/while/return/raise."""

from __future__ import annotations


def handle(value: int) -> int:
    """Handle one value."""
    # if value < 0:
    #     return 0
    # for i in range(value):
    #     print(i)
    result = value * 2
    # while result > 100:
    #     result //= 2
    # return result + 1
    return result


def guard(token: str) -> None:
    # if not token:
    #     raise ValueError("missing token")
    # elif len(token) < 8:
    #     raise ValueError("token too short")
    pass


# try:
#     run()
# except Exception as exc:
#     log.exception(exc)
#     raise
