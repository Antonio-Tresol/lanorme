# why: negative - request and response row parsers map distinct column sets with distinct coercions; every assignment differs, so the mapping itself is the meaning rather than shared logic.
from __future__ import annotations


def parse_request_row(row):
    record = {}
    record["method"] = row[0].upper()
    record["path"] = row[1]
    record["query"] = dict(p.split("=") for p in row[2].split("&") if p)
    record["body_bytes"] = int(row[3])
    record["received_at"] = row[4]
    return record


def parse_response_row(row):
    record = {}
    record["status"] = int(row[0])
    record["latency_ms"] = float(row[1])
    record["content_type"] = row[2].lower()
    record["cached"] = row[3] == "HIT"
    record["sent_at"] = row[4]
    record["size"] = int(row[5])
    return record
