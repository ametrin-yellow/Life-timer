"""
POST /events       — принять батч событий от клиента
GET  /events       — отдать события после указанного timestamp (для других устройств)
"""
import json
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models import DeviceEvent, User
from schemas import EventBatchIn, EventResponse
from security import get_current_user

router = APIRouter(prefix="/events", tags=["events"])


@router.post("", status_code=201)
async def push_events(
    batch: EventBatchIn,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Принять батч событий от клиента и сохранить."""
    for ev in batch.events:
        db.add(DeviceEvent(
            user_id     = current_user.id,
            device_id   = ev.device_id,
            event_type  = ev.event_type,
            payload     = json.dumps(ev.payload),
            occurred_at = ev.occurred_at,
        ))
    await db.commit()
    return {"accepted": len(batch.events)}


@router.get("", response_model=list[EventResponse])
async def pull_events(
    after:     datetime,
    device_id: Optional[str] = Query(None, description="Исключить события с этого устройства"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Вернуть события пользователя после указанного occurred_at.
    device_id — фильтр чтобы не получать обратно свои же события.
    """
    q = (
        select(DeviceEvent)
        .where(DeviceEvent.user_id == current_user.id)
        .where(DeviceEvent.occurred_at > after)
        .order_by(DeviceEvent.occurred_at)
    )
    if device_id:
        q = q.where(DeviceEvent.device_id != device_id)

    result = await db.execute(q)
    rows = result.scalars().all()

    # payload хранится как JSON-строка, парсим обратно в dict
    out = []
    for row in rows:
        out.append(EventResponse(
            id          = row.id,
            device_id   = row.device_id,
            event_type  = row.event_type,
            payload     = json.loads(row.payload),
            occurred_at = row.occurred_at,
            received_at = row.received_at,
        ))
    return out