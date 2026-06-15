# why: positive - two notification senders that drifted by reordering two
# why: independent setup lines and renaming one keyword argument. Both edits are
# why: DRY-001 blind spots; the bodies remain one extractable send routine.
"""Two senders differing by reordered setup lines and one kwarg name."""

from __future__ import annotations


def send_email(gateway, user, body):
    payload = {"body": body}
    recipient = user.email
    payload["to"] = recipient
    handle = gateway.dispatch(payload, channel="email")
    return handle.tracking_id


def send_sms(gateway, user, body):
    recipient = user.phone
    payload = {"body": body}
    payload["to"] = recipient
    handle = gateway.dispatch(payload, transport="email")
    return handle.tracking_id
