import uuid
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from models import UserSettings, DayPlan, Task, TaskStatus


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def user_today(day_start_hour: int = 0, tz_name: str = "UTC") -> date:
    tz = ZoneInfo(tz_name)
    local_now = datetime.now(tz)
    return (local_now - timedelta(hours=day_start_hour)).date()


def day_boundary(today: date, day_start_hour: int, tz_name: str = "UTC") -> datetime:
    tz = ZoneInfo(tz_name)
    local_boundary = datetime(today.year, today.month, today.day, day_start_hour, tzinfo=tz)
    return local_boundary.astimezone(timezone.utc)


def next_day_boundary(day_start_hour: int, tz_name: str = "UTC") -> datetime:
    today = user_today(day_start_hour, tz_name)
    tomorrow = today + timedelta(days=1)
    return day_boundary(tomorrow, day_start_hour, tz_name)


async def get_user_day_settings(user_id: int, db: AsyncSession) -> tuple[int, str]:
    result = await db.execute(
        select(UserSettings.day_start_hour, UserSettings.timezone)
        .where(UserSettings.user_id == user_id)
    )
    row = result.one_or_none()
    if row is None:
        return 0, "UTC"
    return row[0] or 0, row[1] or "UTC"


async def get_or_create_today_plan(
    user_id: int, db: AsyncSession,
    day_start_hour: int | None = None,
    tz_name: str | None = None,
) -> DayPlan:
    if day_start_hour is None or tz_name is None:
        dsh, tz = await get_user_day_settings(user_id, db)
        if day_start_hour is None:
            day_start_hour = dsh
        if tz_name is None:
            tz_name = tz

    today = user_today(day_start_hour, tz_name)
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

    boundary = day_boundary(today, day_start_hour, tz_name)

    has_active_carryover = False

    plan = DayPlan(user_id=user_id, date=today)
    db.add(plan)
    await db.flush()

    if prev_plan:
        for task in prev_plan.tasks:
            new_task = _carry_over_task(task, plan.id, boundary, today)
            if new_task is None:
                continue
            if new_task.started_at is not None:
                has_active_carryover = True
            db.add(new_task)

    scheduled_result = await db.execute(
        select(Task)
        .join(DayPlan)
        .where(
            DayPlan.user_id == user_id,
            Task.scheduled_date == today,
            Task.plan_id != plan.id,
            Task.status.in_([TaskStatus.PENDING, TaskStatus.ACTIVE]),
        )
    )
    for task in scheduled_result.scalars().all():
        new_task = Task(
            id=str(uuid.uuid4()),
            plan_id=plan.id,
            name=task.name,
            allocated_seconds=task.allocated_seconds,
            elapsed_seconds=0,
            status=TaskStatus.PENDING,
            scheduled_time=task.scheduled_time,
            position=task.position,
            priority=task.priority,
            is_recurring=False,
            schedule_days=None,
            scheduled_date=today,
        )
        db.add(new_task)

    plan.procrastination_started_at = None if has_active_carryover else utcnow()

    await db.commit()

    result = await db.execute(
        select(DayPlan)
        .where(DayPlan.id == plan.id)
        .options(selectinload(DayPlan.tasks))
    )
    return result.scalar_one()


def _matches_schedule(task: Task, target_date: date) -> bool:
    if not task.schedule_days:
        return True
    days = {int(d) for d in task.schedule_days.split(",")}
    return target_date.isoweekday() in days


def _carry_over_task(task: Task, new_plan_id: int, boundary: datetime, target_date: date) -> Task | None:
    if task.is_recurring:
        if not _matches_schedule(task, target_date):
            if task.started_at is not None:
                delta = max(0, int((boundary - task.started_at).total_seconds()))
                task.elapsed_seconds += delta
                task.started_at = None
                task.status = TaskStatus.COMPLETED
            return None
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
        schedule_days=task.schedule_days,
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
