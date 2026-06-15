# why: positive - two nested-loop flatteners copy-pasted then drifted only by an incidental log line message; the nested structure and calls match exactly, the body should be shared.
from __future__ import annotations

import logging

log = logging.getLogger(__name__)


def flatten_groups(groups):
    result = []
    total = 0
    for group in groups:
        for item in group.members:
            if item.active:
                result.append(item.key)
                total += 1
    log.info("flattened groups")
    return result


def flatten_buckets(buckets):
    result = []
    total = 0
    for bucket in buckets:
        for item in bucket.members:
            if item.active:
                result.append(item.key)
                total += 1
    log.info("merged buckets done")
    return result
