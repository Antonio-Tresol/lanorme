"""Disabled function and method call statements."""

from __future__ import annotations


def process(user_id: int) -> None:
    """Process a user."""
    record = fetch(user_id)
    # log.debug("processing user=%s", user_id)
    # metrics.increment("process.start")
    transform(record)
    # cache.set(f"user:{user_id}", record, ttl=300)
    # notifier.send(user_id, "processed")
    save(record)
    # audit.write(user_id, "processed")


def fetch(uid: int) -> dict:
    return {"id": uid}


def transform(record: dict) -> None:
    record["ok"] = True


def save(record: dict) -> None:
    pass


# print("debug: starting up")
# breakpoint()
# pdb.set_trace()
