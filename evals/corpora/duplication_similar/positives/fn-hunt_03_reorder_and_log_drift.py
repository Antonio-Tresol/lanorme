# why: positive - two retry loops copy-pasted then drifted by two reordered independent setup lines and a different warning message; reviewer would extract a shared retry helper.
from __future__ import annotations

import time
import logging

log = logging.getLogger(__name__)


def fetch_profile(client, key):
    attempt = 0
    last_error = None
    deadline = time.monotonic()
    while attempt < 4:
        try:
            return client.load(key)
        except ConnectionError as exc:
            last_error = exc
            attempt += 1
            log.warning("profile fetch failed")
            time.sleep(attempt)
    raise last_error


def fetch_settings(client, key):
    last_error = None
    attempt = 0
    deadline = time.monotonic()
    while attempt < 4:
        try:
            return client.load(key)
        except ConnectionError as exc:
            last_error = exc
            attempt += 1
            log.warning("settings fetch unavailable")
            time.sleep(attempt)
    raise last_error
