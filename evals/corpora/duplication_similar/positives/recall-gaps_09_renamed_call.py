# why: positive - two persistence routines copy-pasted; one method call was
# why: renamed (save vs persist) during drift. DRY-001 keeps the call name in
# why: the dump so it misses it; the obvious fix is a single shared writer.
"""Two writers differing only by a renamed method call."""

from __future__ import annotations


def store_event(repo, event):
    record = repo.prepare(event)
    record.stamp()
    repo.save(record)
    repo.flush()
    return record.id


def store_alert(repo, alert):
    record = repo.prepare(alert)
    record.stamp()
    repo.persist(record)
    repo.flush()
    return record.id
