# why: positive - two FastAPI fetch-or-404 handlers are copy-paste drift differing by one added statement and a renamed attribute; a shared get_or_404 helper removes real duplicated logic.
from __future__ import annotations

from fastapi import APIRouter, HTTPException

router = APIRouter()


@router.get("/users/{user_id}")
async def get_user(user_id: int, session, logger):
    record = await session.get("User", user_id)
    if record is None:
        logger.warning("user lookup miss")
        raise HTTPException(status_code=404, detail="not found")
    record.last_seen = "now"
    await session.refresh(record)
    return record


@router.get("/teams/{team_id}")
async def get_team(team_id: int, session, logger):
    record = await session.get("Team", team_id)
    if record is None:
        logger.warning("team lookup miss")
        raise HTTPException(status_code=404, detail="not found")
    record.touched_at = "now"
    await session.refresh(record)
    await session.flush()
    return record
