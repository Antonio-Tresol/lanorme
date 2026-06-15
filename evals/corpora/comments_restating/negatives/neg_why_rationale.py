"""Why/rationale comments: they explain motivation, not the mechanics.

None of these should be flagged; each adds a reason the code could not convey.
"""

from __future__ import annotations

import time


def fetch(url: str, retries: int = 3):
    # Retry because the upstream API returns 503 under load.
    for attempt in range(retries):
        result = _get(url)
        if result is not None:
            return result
        # Back off exponentially to avoid hammering a struggling server.
        time.sleep(2 ** attempt)
    return None


def _get(url: str):
    return {"url": url}


def parse_amount(raw: str) -> int:
    # Strip commas first; the locale formats thousands as "1,000".
    raw = raw.replace(",", "")
    return int(raw)


def dedupe(items: list[int]) -> list[int]:
    # A dict preserves insertion order, so this keeps the first occurrence.
    return list(dict.fromkeys(items))


def normalize(name: str) -> str:
    # Casefold rather than lower so that German "ß" compares correctly.
    return name.casefold()
