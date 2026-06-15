"""Restating comments where the verb literally appears as an identifier.

These name the function or keyword used on the next line, so the comment is
pure duplication of the code token.
"""

from __future__ import annotations

import json


def handlers(result, items, payload, parser, url):
    # return result
    return result


def save(items: list[int]) -> None:
    # sort items
    items.sort()


def dump(payload: dict[str, int]) -> str:
    # dumps payload
    return json.dumps(payload)


def read(parser, url: str):
    # parse url
    return parser.parse(url)


def append_all(items: list[int], value: int) -> None:
    # append value
    items.append(value)


def close_connection(connection) -> None:
    # close connection
    connection.close()
