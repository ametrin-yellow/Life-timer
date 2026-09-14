import uuid
from datetime import date, datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from models import UserSettings, DayPlan, Task, TaskStatus


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def user_today(day_start_hour: int = 0) -> date:
    return (utcnow() - timedelta(hours=day_start_hour)).date()


async def get_day_start_hour(user_id: int, db: AsyncSession) -> int:
    result = await db.execute(
        select(UserSettings.day_start_hour).where(UserSettings.user_id == user_id)
    )
    return result.scalar_one_or_none() or 0


async def get_or_create_today_plan(
    user_id: int, db: AsyncSession, day_start_hour: int | None = None,
) -> DayPlan:
    if day_start_hour is None:
        day_start_hour = await get_day_start_hour(user_id, db)
    today = user_today(day_start_hour)
    result = await db.execute(
        select(DayPlan)
        .where(DayPlan.user_id == user_id, DayPlan.date == today)
        .options(selectinload(DayPlan.tasks))
    )
    plan = result.scalar_one_or_none()
    if plan:
        return plan

    prev_result = await db.execute(
        select(DayPlan)
        .where(DayPlan.user_id == user_id, DayPlan.date < today)
        .options(selectinload(DayPlan.tasks))
        .order_by(DayPlan.date.desc())
        .limit(1)
    )
    prev_plan = prev_result.scalar_one_or_none()

    boundary = datetime(
        today.year, today.month, today.day,
        day_start_hour, tzinfo=timezone.utc,
    )

    has_active_carryover = False

    plan = DayPlan(user_id=user_id, date=today)
    db.add(plan)
    await db.flush()

    if prev_plan:
        for task in prev_plan.tasks:
            new_task = _carry_over_task(task, plan.id, boundary)
            if new_task is None:
                continue
            if new_task.started_at is not None:
                has_active_carryover = True
            db.add(new_task)

    plan.procrastination_started_at = None if has_active_carryover else utcnow()

    await db.commit()

    result = await db.execute(
        select(DayPlan)
        .where(DayPlan.id == plan.id)
        .options(selectinload(DayPlan.tasks))
    )
    return result.scalar_one()


def _carry_over_task(task: Task, new_plan_id: int, boundary: datetime) -> Task | None:
    if task.is_recurring:
        return _carry_recurring(task, new_plan_id, boundary)
    return _carry_onetime(task, new_plan_id, boundary)


def _carry_recurring(task: Task, new_plan_id: int, boundary: datetime) -> Task:
    new_started_at = None

    if task.started_at is not None:
        delta = max(0, int((boundary - task.started_at).total_seconds()))
        task.elapsed_seconds += delta
        task.started_at = None
        task.status = TaskStatus.COMPLETED
        new_started_at = boundary

    return Task(
        id=str(uuid.uuid4()),
        plan_id=new_plan_id,
        name=task.name,
        allocated_seconds=task.allocated_seconds,
        elapsed_seconds=0,
        status=TaskStatus.ACTIVE if new_started_at else TaskStatus.PENDING,
        scheduled_time=task.scheduled_time,
        position=task.position,
        priority=task.priority,
        is_recurring=True,
        started_at=new_started_at,
    )


def _carry_onetime(task: Task, new_plan_id: int, boundary: datetime) -> Task | None:
    if task.status in (TaskStatus.COMPLETED, TaskStatus.SKIPPED):
        return None

    new_started_at = None
    new_allocated = task.allocated_seconds

    if task.started_at is not None:
        delta = max(0, int((boundary - task.started_at).total_seconds()))
        task.elapsed_seconds += delta
        task.started_at = None

        if task.allocated_seconds > 0:
            new_allocated = max(0, task.allocated_seconds - task.elapsed_seconds)

        new_started_at = boundary
    else:
        if task.allocated_seconds > 0:
            new_allocated = max(0, task.allocated_seconds - task.elapsed_seconds)

    return Task(
        id=str(uuid.uuid4()),
        plan_id=new_plan_id,
        name=task.name,
        allocated_seconds=new_allocated,
        elapsed_seconds=0,
        status=TaskStatus.ACTIVE if new_started_at else TaskStatus.PENDING,
        scheduled_time=task.scheduled_time,
        position=task.position,
        priority=task.priority,
        is_recurring=False,
        started_at=new_started_at,
    )
