from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_db
from models import User, DayPlan, Task, TaskStatus
from schemas import TimerStateResponse, TaskResponse
from security import get_current_user, decode_token
from day import utcnow, get_or_create_today_plan
from ws import manager

router = APIRouter()


def _compute_procrastination(plan: DayPlan, now: datetime) -> int:
    total = plan.procrastination_used
    if plan.procrastination_started_at is not None:
        total += int((now - plan.procrastination_started_at).total_seconds())
    return total


def _find_active_task(plan: DayPlan) -> Task | None:
    for task in plan.tasks:
        if task.started_at is not None:
            return task
    return None


async def _get_task_in_plan(
    task_id: str, plan: DayPlan, db: AsyncSession,
) -> Task:
    for task in plan.tasks:
        if task.id == task_id:
            return task
    raise HTTPException(status_code=404, detail="Задача не найдена")


def _stop_task(task: Task, now: datetime) -> int:
    """Stop a running task, accumulate elapsed. Returns seconds accumulated."""
    if task.started_at is None:
        return 0
    delta = int((now - task.started_at).total_seconds())
    task.elapsed_seconds += delta
    task.started_at = None
    return delta


def _stop_procrastination(plan: DayPlan, now: datetime):
    if plan.procrastination_started_at is not None:
        plan.procrastination_used += int(
            (now - plan.procrastination_started_at).total_seconds()
        )
        plan.procrastination_started_at = None


def _start_procrastination(plan: DayPlan, now: datetime):
    if plan.procrastination_started_at is None:
        plan.procrastination_started_at = now


async def _broadcast_state(user_id: int, plan: DayPlan, now: datetime):
    state = _build_state(plan, now)
    await manager.broadcast_to_user(user_id, state.model_dump(mode="json"))


def _build_state(plan: DayPlan, now: datetime) -> TimerStateResponse:
    active = _find_active_task(plan)
    return TimerStateResponse(
        plan_id=plan.id,
        date=plan.date,
        server_time=now,
        active_task_id=active.id if active else None,
        procrastination_seconds=_compute_procrastination(plan, now),
        procrastination_running=plan.procrastination_started_at is not None,
        tasks=[TaskResponse.model_validate(t) for t in plan.tasks],
        day_finalized=plan.day_finalized,
    )


@router.get("/state", response_model=TimerStateResponse)
async def get_state(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    plan = await get_or_create_today_plan(current_user.id, db)
    return _build_state(plan, utcnow())


@router.post("/tasks/{task_id}/start", response_model=TimerStateResponse)
async def start_task(
    task_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    plan = await get_or_create_today_plan(current_user.id, db)
    if plan.day_finalized:
        raise HTTPException(status_code=400, detail="День финализирован")

    now = utcnow()
    task = await _get_task_in_plan(task_id, plan, db)

    if task.status in (TaskStatus.COMPLETED, TaskStatus.SKIPPED):
        raise HTTPException(status_code=400, detail="Задача уже завершена")

    if task.started_at is not None:
        raise HTTPException(status_code=400, detail="Задача уже запущена")

    active = _find_active_task(plan)
    if active and active.id != task_id:
        _stop_task(active, now)
        active.status = TaskStatus.PENDING

    _stop_procrastination(plan, now)

    task.status = TaskStatus.ACTIVE
    task.started_at = now

    await db.commit()
    state = _build_state(plan, utcnow())
    await _broadcast_state(current_user.id, plan, utcnow())
    return state


@router.post("/tasks/{task_id}/pause", response_model=TimerStateResponse)
async def pause_task(
    task_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    plan = await get_or_create_today_plan(current_user.id, db)
    now = utcnow()
    task = await _get_task_in_plan(task_id, plan, db)

    if task.started_at is None:
        raise HTTPException(status_code=400, detail="Задача не запущена")

    _stop_task(task, now)
    task.status = TaskStatus.PENDING
    _start_procrastination(plan, now)

    await db.commit()
    state = _build_state(plan, utcnow())
    await _broadcast_state(current_user.id, plan, utcnow())
    return state


@router.post("/tasks/{task_id}/complete", response_model=TimerStateResponse)
async def complete_task(
    task_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    plan = await get_or_create_today_plan(current_user.id, db)
    now = utcnow()
    task = await _get_task_in_plan(task_id, plan, db)

    if task.status in (TaskStatus.COMPLETED, TaskStatus.SKIPPED):
        raise HTTPException(status_code=400, detail="Задача уже завершена")

    _stop_task(task, now)
    task.status = TaskStatus.COMPLETED
    task.completed_at = now
    _start_procrastination(plan, now)

    await db.commit()
    state = _build_state(plan, utcnow())
    await _broadcast_state(current_user.id, plan, utcnow())
    return state


@router.post("/tasks/{task_id}/skip", response_model=TimerStateResponse)
async def skip_task(
    task_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    plan = await get_or_create_today_plan(current_user.id, db)
    now = utcnow()
    task = await _get_task_in_plan(task_id, plan, db)

    if task.status in (TaskStatus.COMPLETED, TaskStatus.SKIPPED):
        raise HTTPException(status_code=400, detail="Задача уже завершена")

    _stop_task(task, now)
    task.status = TaskStatus.SKIPPED
    _start_procrastination(plan, now)

    await db.commit()
    state = _build_state(plan, utcnow())
    await _broadcast_state(current_user.id, plan, utcnow())
    return state


@router.post("/tasks/{task_id}/reopen", response_model=TimerStateResponse)
async def reopen_task(
    task_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    plan = await get_or_create_today_plan(current_user.id, db)
    if plan.day_finalized:
        raise HTTPException(status_code=400, detail="День финализирован")

    task = await _get_task_in_plan(task_id, plan, db)

    if task.status not in (TaskStatus.COMPLETED, TaskStatus.SKIPPED):
        raise HTTPException(status_code=400, detail="Задача не завершена")

    task.status = TaskStatus.PENDING
    task.completed_at = None

    await db.commit()
    state = _build_state(plan, utcnow())
    await _broadcast_state(current_user.id, plan, utcnow())
    return state


# ──────────────────────────────────────────────
#  WebSocket
# ──────────────────────────────────────────────

@router.websocket("/ws")
async def timer_ws(ws: WebSocket):
    token = ws.query_params.get("token")
    if not token:
        await ws.close(code=4001, reason="Missing token")
        return

    try:
        user_id = decode_token(token, expected_type="access")
    except Exception:
        await ws.close(code=4001, reason="Invalid token")
        return

    await manager.connect(user_id, ws)
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect(user_id, ws)
