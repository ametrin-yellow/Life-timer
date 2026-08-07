from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from database import get_db
from models import User, DayPlan, Task, TaskStatus
from schemas import TimerStateResponse, TaskResponse
from security import get_current_user, decode_token
from ws import manager

router = APIRouter()


def _now() -> datetime:
    return datetime.now(timezone.utc)


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


async def _get_today_plan(user: User, db: AsyncSession) -> DayPlan:
    today = date.today()
    result = await db.execute(
        select(DayPlan)
        .where(DayPlan.user_id == user.id, DayPlan.date == today)
        .options(selectinload(DayPlan.tasks))
    )
    plan = result.scalar_one_or_none()
    if not plan:
        plan = DayPlan(
            user_id=user.id,
            date=today,
            procrastination_started_at=_now(),
        )
        db.add(plan)
        await db.commit()
        await db.refresh(plan)
    return plan


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
    plan = await _get_today_plan(current_user, db)
    return _build_state(plan, _now())


@router.post("/tasks/{task_id}/start", response_model=TimerStateResponse)
async def start_task(
    task_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    plan = await _get_today_plan(current_user, db)
    if plan.day_finalized:
        raise HTTPException(status_code=400, detail="День финализирован")

    now = _now()
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
    state = _build_state(plan, _now())
    await _broadcast_state(current_user.id, plan, _now())
    return state


@router.post("/tasks/{task_id}/pause", response_model=TimerStateResponse)
async def pause_task(
    task_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    plan = await _get_today_plan(current_user, db)
    now = _now()
    task = await _get_task_in_plan(task_id, plan, db)

    if task.started_at is None:
        raise HTTPException(status_code=400, detail="Задача не запущена")

    _stop_task(task, now)
    task.status = TaskStatus.PENDING
    _start_procrastination(plan, now)

    await db.commit()
    state = _build_state(plan, _now())
    await _broadcast_state(current_user.id, plan, _now())
    return state


@router.post("/tasks/{task_id}/complete", response_model=TimerStateResponse)
async def complete_task(
    task_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    plan = await _get_today_plan(current_user, db)
    now = _now()
    task = await _get_task_in_plan(task_id, plan, db)

    if task.status in (TaskStatus.COMPLETED, TaskStatus.SKIPPED):
        raise HTTPException(status_code=400, detail="Задача уже завершена")

    _stop_task(task, now)
    task.status = TaskStatus.COMPLETED
    task.completed_at = now
    _start_procrastination(plan, now)

    await db.commit()
    state = _build_state(plan, _now())
    await _broadcast_state(current_user.id, plan, _now())
    return state


@router.post("/tasks/{task_id}/skip", response_model=TimerStateResponse)
async def skip_task(
    task_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    plan = await _get_today_plan(current_user, db)
    now = _now()
    task = await _get_task_in_plan(task_id, plan, db)

    if task.status in (TaskStatus.COMPLETED, TaskStatus.SKIPPED):
        raise HTTPException(status_code=400, detail="Задача уже завершена")

    _stop_task(task, now)
    task.status = TaskStatus.SKIPPED
    _start_procrastination(plan, now)

    await db.commit()
    state = _build_state(plan, _now())
    await _broadcast_state(current_user.id, plan, _now())
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
