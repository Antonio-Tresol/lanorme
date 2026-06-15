"""Multi-line restatement negatives (emergent-intent summaries).

The comment summarises an EMERGENT intent of the block that no single line
in the block names. The block is the implementation; the comment is the
domain-level "why this exists". Should NOT be flagged.
"""

from __future__ import annotations


def histogram(values: list[int]) -> dict[int, int]:
    # normalize then bucket then count
    cleaned = [abs(v) % 10 for v in values]
    bucketed = [v // 2 for v in cleaned]
    out: dict[int, int] = {}
    for b in bucketed:
        out[b] = out.get(b, 0) + 1
    return out


def safe_username(raw: str) -> str:
    # defend against the homoglyph-spoofing attack described in SEC-2024-014
    s = raw.strip()
    s = s.replace("а", "a")
    s = s.replace("о", "o")
    return s.lower()


def reconcile(local: dict[str, int], remote: dict[str, int]) -> dict[str, int]:
    # last-write-wins with remote priority, except for soft-deleted keys
    out = dict(local)
    for k, v in remote.items():
        if v == -1:
            continue
        out[k] = v
    return out


def parse_money(raw: str) -> int:
    # accept the three currency formats finance uses in their CSV exports
    s = raw.strip().replace(",", "").replace("$", "")
    if s.endswith("USD"):
        s = s[:-3].strip()
    return int(float(s) * 100)


def schedule(jobs: list[str]) -> list[str]:
    # fair scheduling: round-robin across tenants, then FIFO within tenant
    by_tenant: dict[str, list[str]] = {}
    for job in jobs:
        tenant = job.split(":", 1)[0]
        by_tenant.setdefault(tenant, []).append(job)
    out: list[str] = []
    while any(by_tenant.values()):
        for tenant in list(by_tenant):
            if by_tenant[tenant]:
                out.append(by_tenant[tenant].pop(0))
    return out
