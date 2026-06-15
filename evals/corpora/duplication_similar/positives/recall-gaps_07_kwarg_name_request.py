# why: positive - two HTTP wrappers built by copy-paste; the only difference is
# why: a keyword-argument name passed to the client call. DRY-001 keeps kwarg
# why: names in the dump so it misses this; the fix is a single shared wrapper.
"""Two request helpers differing only by a keyword-argument name."""

from __future__ import annotations


def get_json(client, url):
    response = client.request("GET", url, timeout=30)
    response.raise_for_status()
    body = response.json()
    if not isinstance(body, dict):
        raise ValueError("expected an object")
    return body


def get_xml(client, url):
    response = client.request("GET", url, deadline=30)
    response.raise_for_status()
    body = response.json()
    if not isinstance(body, dict):
        raise ValueError("expected an object")
    return body
