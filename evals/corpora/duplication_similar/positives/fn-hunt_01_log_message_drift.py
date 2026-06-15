# why: positive - two identical aggregation loops copy-pasted then drifted only by their debug log message text; the log strings are incidental, the body should be a shared helper.
from __future__ import annotations

import logging

log = logging.getLogger(__name__)


def total_active_users(records):
    running = 0
    seen = 0
    for record in records:
        if not record.enabled:
            continue
        running += record.weight
        seen += 1
    log.debug("counted active users")
    return running


def total_active_sessions(records):
    running = 0
    seen = 0
    for record in records:
        if not record.enabled:
            continue
        running += record.weight
        seen += 1
    log.debug("counted live sessions")
    return running
