"""
Репозиторий — единственное место где код касается БД.
Бизнес-логика работает только через этот слой.
"""
from datetime import date, datetime
from typing import Optional
from sqlalchemy.orm import Session

from lt_db import (
    get_session, DayPlan, Task, Settings, CoinBalance,
    CoinTransaction, Reward, Template, Preset, PresetItem,
    TaskStatus, RewardType, Priority
)


# ──────────────────────────────────────────────
#  Settings
# ──────────────────────────────────────────────

def get_settings() -> Settings:
    with get_session() as s:
        obj = s.get(Settings, 1)
        s.expunge(obj)
        return obj


def save_settings(data: dict):
    with get_session() as s:
        obj = s.get(Settings, 1)
        for k, v in data.items():
            setattr(obj, k, v)
        s.commit()


# ──────────────────────────────────────────────
#  DayPlan
# ──────────────────────────────────────────────

def get_or_create_plan(d: date) -> DayPlan:
    with get_session() as s:
        plan = s.query(DayPlan).filter_by(date=d).first()
        if not plan:
            plan = DayPlan(date=d)
            s.add(plan)
            s.commit()
            s.refresh(plan)
        s.expunge(plan)
        return plan


def get_plan_with_tasks(d: date) -> Optional[DayPlan]:
    with get_session() as s:
        from sqlalchemy.orm import joinedload
        plan = (s.query(DayPlan)
                .options(joinedload(DayPlan.tasks))
                .filter_by(date=d)
                .first())
        if plan:
            s.expunge_all()
        return plan


def update_plan(plan_id: int, **kwargs):
    with get_session() as s:
        plan = s.get(DayPlan, plan_id)
        for k, v in kwargs.items():
            setattr(plan, k, v)
        s.commit()


def mark_carried_over(task_ids: list[str]) -> None:
    """Помечает задачи как перенесённые — больше не будут предлагаться к переносу."""
    if not task_ids:
        return
    with get_session() as s:
        s.query(Task).filter(Task.id.in_(task_ids)).update(
            {"carried_over": True}, synchronize_session=False
        )
        s.commit()


def get_unfinished_from_date(d: date) -> list[Task]:
    """Незавершённые задачи за конкретный день которые ещё не переносились."""
    with get_session() as s:
        from sqlalchemy.orm import joinedload
        plan = (s.query(DayPlan)
                .options(joinedload(DayPlan.tasks))
                .filter_by(date=d)
                .first())
        if not plan:
            return []
        result = [t for t in plan.tasks
                  if t.status in (TaskStatus.PENDING, TaskStatus.ACTIVE)
                  and not t.carried_over]
        s.expunge_all()
        return result


# ──────────────────────────────────────────────
#  Tasks
# ──────────────────────────────────────────────

def add_task(plan_id: int, task_id: str, name: str,
             allocated_seconds: int, scheduled_time: Optional[str] = None,
             position: int = 0, priority: Priority = Priority.NORMAL) -> Task:
    with get_session() as s:
        t = Task(
            id=task_id,
            plan_id=plan_id,
            name=name,
            allocated_seconds=allocated_seconds,
            scheduled_time=scheduled_time,
            position=position,
            priority=priority,
        )
        s.add(t)
        s.commit()
        s.refresh(t)
        return t


def update_task(task_id: str, **kwargs):
    with get_session() as s:
        t = s.get(Task, task_id)
        if not t:
            return
        for k, v in kwargs.items():
            setattr(t, k, v)
        s.commit()


def delete_task(task_id: str):
    with get_session() as s:
        t = s.get(Task, task_id)
        if t:
            s.delete(t)
            s.commit()


def get_tasks_for_plan(plan_id: int) -> list[Task]:
    with get_session() as s:
        return (s.query(Task)
                .filter_by(plan_id=plan_id)
                .order_by(Task.position)
                .all())


# ──────────────────────────────────────────────
#  Геймификация — баланс
# ──────────────────────────────────────────────

def get_balance() -> CoinBalance:
    with get_session() as s:
        obj = s.get(CoinBalance, 1)
        s.expunge(obj)
        return obj


def add_transaction(amount: int, reason: str,
                    task_id: Optional[str] = None,
                    plan_date: Optional[date] = None,
                    reward_id: Optional[int] = None) -> int:
    """Добавляет транзакцию и возвращает новый баланс."""
    with get_session() as s:
        bal = s.get(CoinBalance, 1)
        settings = s.get(Settings, 1)

        new_balance = bal.balance + amount

        # Покупки не уводят в минус никогда
        if amount < 0 and reward_id is not None:
            if bal.balance <= 0:
                raise ValueError("Недостаточно коинов")
            new_balance = max(0, new_balance)

        # Штрафы уводят в минус только если разрешено
        if amount < 0 and reward_id is None:
            if not settings.allow_negative_balance:
                new_balance = max(0, new_balance)

        bal.balance = new_balance
        s.add(CoinTransaction(
            amount=amount,
            reason=reason,
            task_id=task_id,
            plan_date=plan_date,
            reward_id=reward_id,
        ))
        s.commit()
        return new_balance


def update_streak(streak: int):
    with get_session() as s:
        bal = s.get(CoinBalance, 1)
        bal.streak = streak
        s.commit()


def get_transactions(limit: int = 50) -> list[CoinTransaction]:
    with get_session() as s:
        return (s.query(CoinTransaction)
                .order_by(CoinTransaction.created_at.desc())
                .limit(limit)
                .all())


# ──────────────────────────────────────────────
#  Магазин
# ──────────────────────────────────────────────

def get_rewards(active_only: bool = True) -> list[Reward]:
    with get_session() as s:
        q = s.query(Reward)
        if active_only:
            q = q.filter_by(is_active=True)
        return q.order_by(Reward.price).all()


def add_reward(name: str, price: int, reward_type: RewardType,
               description: Optional[str] = None,
               count: Optional[int] = None,
               task_duration_minutes: Optional[int] = None) -> Reward:
    with get_session() as s:
        r = Reward(
            name=name, price=price, reward_type=reward_type,
            description=description,
            count=count, count_initial=count,
            task_duration_minutes=task_duration_minutes,
        )
        s.add(r)
        s.commit()
        s.refresh(r)
        return r


def purchase_reward(reward_id: int) -> dict:
    """Покупает поощрение. Возвращает dict с new_balance и reward. Raises ValueError если нельзя."""
    with get_session() as s:
        r = s.get(Reward, reward_id)
        if not r or not r.is_active:
            raise ValueError("Поощрение недоступно")
        if r.reward_type == RewardType.LIMITED and r.count <= 0:
            raise ValueError("Товар закончился")

        bal = s.get(CoinBalance, 1)
        if bal.balance < r.price:
            raise ValueError("Недостаточно коинов")
        bal.balance -= r.price

        s.add(CoinTransaction(
            amount=-r.price,
            reason=f"Покупка: {r.name}",
            reward_id=reward_id,
        ))

        if r.reward_type == RewardType.LIMITED:
            r.count -= 1

        s.commit()
        return {
            "new_balance": bal.balance,
            "reward_name": r.name,
            "reward_price": r.price,
            "reward_type": r.reward_type,
            "task_duration_minutes": r.task_duration_minutes,
        }


def delete_reward(reward_id: int):
    with get_session() as s:
        r = s.get(Reward, reward_id)
        if r:
            s.delete(r)
            s.commit()


def update_reward(reward_id: int, name: str, price: int, description: Optional[str],
                  count_add: int = 0, task_duration_minutes: Optional[int] = None):
    """
    Обновляет название, цену, описание награды.
    count_add — сколько добавить к остатку (для пополнения лимитированных).
    task_duration_minutes — для абонементов: длительность создаваемой задачи.
    """
    with get_session() as s:
        r = s.get(Reward, reward_id)
        if not r:
            raise ValueError("Награда не найдена")
        r.name = name
        r.price = price
        r.description = description or None
        if r.reward_type == RewardType.SUBSCRIPTION:
            r.task_duration_minutes = task_duration_minutes or None
        if count_add > 0 and r.reward_type == RewardType.LIMITED:
            r.count = (r.count or 0) + count_add
            r.count_initial = (r.count_initial or 0) + count_add
        s.commit()


# ──────────────────────────────────────────────
#  Шаблоны и пресеты
# ──────────────────────────────────────────────

def get_templates() -> list[Template]:
    with get_session() as s:
        return s.query(Template).order_by(Template.category, Template.name).all()


def add_user_template(name: str, allocated_seconds: int, category: str) -> Template:
    with get_session() as s:
        t = Template(name=name, allocated_seconds=allocated_seconds,
                     category=category, is_builtin=False)
        s.add(t)
        s.commit()
        s.refresh(t)
        return t


def delete_user_template(template_id: int):
    with get_session() as s:
        t = s.get(Template, template_id)
        if t and not t.is_builtin:
            s.delete(t)
            s.commit()


def get_presets() -> list[Preset]:
    with get_session() as s:
        return s.query(Preset).all()


def add_user_preset(name: str, template_ids: list[int]) -> Preset:
    with get_session() as s:
        p = Preset(name=name, is_builtin=False)
        s.add(p)
        s.flush()
        for i, tid in enumerate(template_ids):
            s.add(PresetItem(preset_id=p.id, template_id=tid, position=i))
        s.commit()
        s.refresh(p)
        return p


def delete_user_preset(preset_id: int):
    with get_session() as s:
        p = s.get(Preset, preset_id)
        if p and not p.is_builtin:
            s.delete(p)
            s.commit()


# ──────────────────────────────────────────────
#  Статистика
# ──────────────────────────────────────────────

def get_stats(date_from=None, date_to=None) -> list[dict]:
    """
    Посуточная статистика за [date_from, date_to].
    date_from=None — с самого начала.
    """
    from sqlalchemy.orm import joinedload
    if date_to is None:
        date_to = date.today()
    with get_session() as s:
        q = (s.query(DayPlan)
               .options(joinedload(DayPlan.tasks))
               .filter(DayPlan.date <= date_to))
        if date_from is not None:
            q = q.filter(DayPlan.date >= date_from)
        plans = q.order_by(DayPlan.date.desc()).all()
        result = []
        for plan in plans:
            tasks = plan.tasks
            completed = sum(1 for t in tasks if t.status == TaskStatus.COMPLETED)
            skipped   = sum(1 for t in tasks if t.status == TaskStatus.SKIPPED)
            overrun   = sum(t.overrun_seconds for t in tasks)
            result.append({
                "date":               plan.date.isoformat(),
                "tasks_total":        len(tasks),
                "tasks_completed":    completed,
                "tasks_skipped":      skipped,
                "elapsed_min":        sum(t.elapsed_seconds for t in tasks) // 60,
                "allocated_min":      sum(t.allocated_seconds for t in tasks) // 60,
                "overrun_min":        overrun // 60,
                "procrastination_min": plan.procrastination_used // 60,
                "coins_earned":       plan.day_bonus,
                "coins_penalty":      plan.day_penalty,
                "coins_total":        plan.day_total,
            })
        return result


# ──────────────────────────────────────────────
#  Compat-методы для старого UI шаблонов/пресетов
# ──────────────────────────────────────────────

def get_templates_as_dicts() -> list[dict]:
    with get_session() as s:
        from lt_db import Template
        return [
            {"id": t.id, "name": t.name,
             "allocated_seconds": t.allocated_seconds,
             "category": t.category, "builtin": t.is_builtin}
            for t in s.query(Template).order_by(Template.category, Template.name).all()
        ]


def save_templates_compat(templates: list[dict]):
    """Сохраняет только пользовательские шаблоны (не встроенные)."""
    with get_session() as s:
        from lt_db import Template
        # Удаляем старые пользовательские
        s.query(Template).filter_by(is_builtin=False).delete()
        for t in templates:
            if not t.get("builtin"):
                s.add(Template(
                    name=t["name"],
                    allocated_seconds=t["allocated_seconds"],
                    category=t.get("category", "👤 Мои шаблоны"),
                    is_builtin=False,
                ))
        s.commit()


def get_user_presets_as_dicts() -> list[dict]:
    with get_session() as s:
        from lt_db import Preset
        result = []
        for p in s.query(Preset).filter_by(is_builtin=False).all():
            result.append({
                "name": p.name,
                "templates": [item.template.name for item in p.items]
            })
        return result


def save_user_presets_compat(presets: list[dict]):
    with get_session() as s:
        from lt_db import Preset, PresetItem, Template
        s.query(Preset).filter_by(is_builtin=False).delete()
        for p_data in presets:
            p = Preset(name=p_data["name"], is_builtin=False)
            s.add(p)
            s.flush()
            for i, tname in enumerate(p_data.get("templates", [])):
                t = s.query(Template).filter_by(name=tname).first()
                if t:
                    s.add(PresetItem(preset_id=p.id, template_id=t.id, position=i))
        s.commit()


def get_stats_summary(date_from=None, date_to=None) -> dict:
    """
    Агрегированная статистика для StatsPanel.
    date_from=None — с самого начала.
    """
    if date_to is None:
        date_to = date.today()
    daily = get_stats(date_from=date_from, date_to=date_to)

    total_tasks     = sum(d["tasks_total"]       for d in daily)
    completed_tasks = sum(d["tasks_completed"]   for d in daily)
    skipped_tasks   = sum(d["tasks_skipped"]     for d in daily)
    completion_rate = round(completed_tasks / total_tasks * 100) if total_tasks else 0
    total_allocated = sum(d["allocated_min"]     for d in daily)
    total_elapsed   = sum(d["elapsed_min"]       for d in daily)
    total_overrun   = sum(d["overrun_min"]       for d in daily)
    proc_used       = sum(d["procrastination_min"] for d in daily)
    # Бюджет прокрастинации = дней * 1440 мин минус запланировано
    if date_from is not None:
        days_count = max(1, (date_to - date_from).days + 1)
    else:
        days_count = len(daily) if daily else 1
    proc_budget = max(0, days_count * 1440 - total_allocated)

    return {
        "total_tasks":               total_tasks,
        "completed_tasks":           completed_tasks,
        "skipped_tasks":             skipped_tasks,
        "completion_rate":           completion_rate,
        "total_allocated_min":       total_allocated,
        "total_elapsed_min":         total_elapsed,
        "total_overrun_min":         total_overrun,
        "procrastination_used_min":  proc_used,
        "procrastination_budget_min": proc_budget,
        "daily":                     daily,
    }
