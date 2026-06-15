# why: negative - a paginated list endpoint and an aggregation/stats endpoint look alike (both query then return) but build different result shapes via different reductions; the per-line logic differs throughout.
from __future__ import annotations

from fastapi import APIRouter, Query

router = APIRouter()


@router.get("/invoices")
async def list_invoices(session, status: str = Query("open"), limit: int = 50):
    rows = await session.query("Invoice").where(state=status).limit(limit).all()
    items = [row.summary() for row in rows]
    cursor = rows[-1].id if rows else None
    has_more = len(rows) == limit
    return {"items": items, "next": cursor, "more": has_more, "count": len(items)}


@router.get("/invoices/stats")
async def invoice_stats(session):
    rows = await session.query("Invoice").all()
    total = sum(row.amount for row in rows)
    overdue = len([row for row in rows if row.is_overdue])
    average = total / len(rows) if rows else 0.0
    return {"total": total, "overdue": overdue, "average": average}
