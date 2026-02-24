import uuid
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from database import get_db
from models import User, DayPlan, Task
from schemas import (
    PlanResponse, PlanUpdate,
    TaskCreate, TaskUpdate, TaskResponse,
)
from auth import get_current_user

router = APIRouter()


# ──────────────────────────────────────────────
#  Helpers
# ──────────────────────────────────────────────

async def _get_plan_or_404(
    plan_id: int, user: User, db: AsyncSession, load_tasks: bool = False
) -> DayPlan:
    q = select(DayPlan).where(DayPlan.id == plan_id, DayPlan.user_id == user.id)
    if load_tasks:
        q = q.options(selectinload(DayPlan.tasks))
    result = await db.execute(q)
    plan = result.scalar_one_or_none()
    if not plan:
        raise HTTPException(status_code=404, detail="План не найден")
    return plan


async def _get_task_or_404(task_id: str, user: User, db: AsyncSession) -> Task:
    result = await db.execute(
        select(Task)
        .join(DayPlan)
        .where(Task.id == task_id, DayPlan.user_id == user.id)
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Задача не найдена")
    return task


# ──────────────────────────────────────────────
#  Plans
# ──────────────────────────────────────────────

@router.get("/", response_model=list[PlanResponse])
async def list_plans(
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Список планов пользователя с фильтром по диапазону дат."""
    q = (
        select(DayPlan)
        .where(DayPlan.user_id == current_user.id)
        .options(selectinload(DayPlan.tasks))
        .order_by(DayPlan.date.desc())
    )
    if date_from:
        q = q.where(DayPlan.date >= date_from)
    if date_to:
        q = q.where(DayPlan.date <= date_to)

    result = await db.execute(q)
    return result.scalars().all()


@router.get("/today", response_model=PlanResponse)
async def get_or_create_today(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Получить план на сегодня, создать если не существует."""
    today = date.today()
    result = await db.execute(
        select(DayPlan)
        .where(DayPlan.user_id == current_user.id, DayPlan.date == today)
        .options(selectinload(DayPlan.tasks))
    )
    plan = result.scalar_one_or_none()

    if not plan:
        plan = DayPlan(user_id=current_user.id, date=today)
        db.add(plan)
        await db.commit()
        await db.refresh(plan)
        # selectinload не работает после refresh — tasks будет пустым списком, ок

    return plan


@router.get("/{plan_id}", response_model=PlanResponse)
async def get_plan(
    plan_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await _get_plan_or_404(plan_id, current_user, db, load_tasks=True)


@router.patch("/{plan_id}", response_model=PlanResponse)
async def update_plan(
    plan_id: int,
    data: PlanUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    plan = await _get_plan_or_404(plan_id, current_user, db, load_tasks=True)
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(plan, field, value)
    await db.commit()
    await db.refresh(plan)
    return plan


# ──────────────────────────────────────────────
#  Tasks
# ──────────────────────────────────────────────

@router.post("/{plan_id}/tasks", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(
    plan_id: int,
    data: TaskCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    plan = await _get_plan_or_404(plan_id, current_user, db)
    task = Task(
        id=str(uuid.uuid4()),
        plan_id=plan.id,
        **data.model_dump(),
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)
    return task


@router.patch("/{plan_id}/tasks/{task_id}", response_model=TaskResponse)
async def update_task(
    plan_id: int,
    task_id: str,
    data: TaskUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # plan_id в пути нужен для проверки владельца через _get_plan_or_404
    await _get_plan_or_404(plan_id, current_user, db)
    task = await _get_task_or_404(task_id, current_user, db)

    for field, value in data.model_dump(exclude_none=True).items():
        setattr(task, field, value)
    await db.commit()
    await db.refresh(task)
    return task


@router.delete("/{plan_id}/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(
    plan_id: int,
    task_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await _get_plan_or_404(plan_id, current_user, db)
    task = await _get_task_or_404(task_id, current_user, db)
    await db.delete(task)
    await db.commit()


@router.post("/{plan_id}/tasks/reorder", response_model=list[TaskResponse])
async def reorder_tasks(
    plan_id: int,
    task_ids: list[str],   # новый порядок — список uuid
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Обновить position у задач одним запросом."""
    plan = await _get_plan_or_404(plan_id, current_user, db, load_tasks=True)

    task_map = {t.id: t for t in plan.tasks}
    if set(task_ids) != set(task_map.keys()):
        raise HTTPException(status_code=400, detail="task_ids не совпадают с задачами плана")

    for position, task_id in enumerate(task_ids):
        task_map[task_id].position = position

    await db.commit()
    return sorted(plan.tasks, key=lambda t: t.position)