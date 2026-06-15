"""Restating comments over simple assignments (placeholder should catch these).

Every comment here just echoes the identifiers on the next line of code and
adds nothing a reader could not see for themselves.
"""

from __future__ import annotations


def build(request, items: list[int]):
    # user id
    user_id = request.user.id

    # total
    total = sum(items)

    # result
    result = {"user_id": user_id, "total": total}

    return result


def coordinates(point) -> tuple[int, int]:
    # x
    x = point.x

    # y
    y = point.y

    return x, y


def configure(settings: dict[str, int]) -> int:
    # timeout
    timeout = settings["timeout"]
    return timeout
