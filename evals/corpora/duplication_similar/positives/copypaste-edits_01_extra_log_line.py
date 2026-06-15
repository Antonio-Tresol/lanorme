# why: positive - second function is the first with one extra logging statement spliced in mid-body, classic copy-paste drift a reviewer would extract.
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def export_invoices(records, destination):
    total = 0
    rows = []
    for record in records:
        amount = record.net + record.tax
        rows.append((record.identifier, amount))
        total += amount
    destination.write_header(["id", "amount"])
    destination.write_rows(rows)
    return total


def export_credit_notes(records, destination):
    total = 0
    rows = []
    for record in records:
        amount = record.net + record.tax
        rows.append((record.identifier, amount))
        total += amount
    logger.info("writing %d rows", len(rows))
    destination.write_header(["id", "amount"])
    destination.write_rows(rows)
    return total
