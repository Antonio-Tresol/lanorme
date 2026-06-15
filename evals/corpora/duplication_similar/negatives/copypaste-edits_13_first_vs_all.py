# why: negative - same shape but one returns the FIRST match and exits early while the other accumulates ALL matches; different contract, not a copy-paste.
from __future__ import annotations


def find_first_admin(members, audit):
    audit.start()
    scanned = 0
    for member in members:
        scanned += 1
        audit.note(member.identifier)
        if member.role == "admin":
            audit.stop(scanned)
            return member
    audit.note("none")
    return None


def collect_all_admins(members, audit):
    audit.start()
    scanned = 0
    found = []
    for member in members:
        scanned += 1
        audit.note(member.identifier)
        if member.role == "admin":
            found.append(member)
    audit.stop(scanned)
    return found
