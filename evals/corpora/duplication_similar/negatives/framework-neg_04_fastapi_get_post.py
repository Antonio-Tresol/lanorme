# why: negative - a read endpoint (fetch-or-404) and a write endpoint (create + commit) share the router shape but have opposite side effects and control flow; they are not collapsible.
from __future__ import annotations

from fastapi import APIRouter, HTTPException

router = APIRouter()


@router.get("/widgets/{widget_id}")
async def get_widget(widget_id: int, session):
    record = await session.get("Widget", widget_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Widget not found")
    record.touch()
    await session.refresh(record)
    return record


@router.post("/widgets")
async def create_widget(payload, session):
    record = payload.to_model()
    session.add(record)
    record.mark_pending()
    await session.commit()
    await session.refresh(record)
    return record
