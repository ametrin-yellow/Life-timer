import json
import os
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Optional

from models import DayPlan, AppSettings


DATA_DIR = Path.home() / ".life_timer"


def _ensure_dir():
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def _day_file(day: str) -> Path:
    return DATA_DIR / f"day_{day}.json"


def load_today() -> DayPlan:
    return load_day(date.today().isoformat())


def load_day(day: str) -> DayPlan:
    _ensure_dir()
    path = _day_file(day)
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            return DayPlan.from_dict(json.load(f))
    settings = load_settings()
    plan = DayPlan(date=day)
    return plan


def save_day(plan: DayPlan):
    _ensure_dir()
    with open(_day_file(plan.date), "w", encoding="utf-8") as f:
        json.dump(plan.to_dict(), f, ensure_ascii=False, indent=2)


def load_settings() -> AppSettings:
    _ensure_dir()
    path = DATA_DIR / "settings.json"
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            return AppSettings.from_dict(json.load(f))
    return AppSettings()


def save_settings(settings: AppSettings):
    _ensure_dir()
    with open(DATA_DIR / "settings.json", "w", encoding="utf-8") as f:
        json.dump(settings.to_dict(), f, ensure_ascii=False, indent=2)


def load_history(days: int = 30) -> list[DayPlan]:
    """Загружает историю за последние N дней для статистики."""
    result = []
    today = date.today()
    for i in range(days):
        d = (today - timedelta(days=i)).isoformat()
        path = _day_file(d)
        if path.exists():
            result.append(load_day(d))
    return result


def get_stats(days: int = 7) -> dict:
    """Базовая статистика за период."""
    history = load_history(days)
    if not history:
        return {}

    total_tasks = 0
    completed_tasks = 0
    total_allocated = 0
    total_elapsed = 0
    total_overrun = 0
    procrastination_used = 0
    procrastination_budget = 0
    daily_stats = []

    for plan in history:
        completed = sum(1 for t in plan.tasks if t.status.value == "completed")
        day_overrun = sum(t.overrun_seconds for t in plan.tasks)
        daily_stats.append({
            "date": plan.date,
            "tasks_total": len(plan.tasks),
            "tasks_completed": completed,
            "allocated_min": plan.total_allocated() // 60,
            "elapsed_min": plan.total_elapsed() // 60,
            "overrun_min": day_overrun // 60,
            "procrastination_used_min": plan.procrastination_used // 60,
            "procrastination_budget_min": max(0, 86400 - plan.total_allocated()) // 60,
        })
        total_tasks += len(plan.tasks)
        completed_tasks += completed
        total_allocated += plan.total_allocated()
        total_elapsed += plan.total_elapsed()
        total_overrun += day_overrun
        procrastination_used += plan.procrastination_used
        procrastination_budget += max(0, 86400 - plan.total_allocated())

    return {
        "period_days": len(history),
        "total_tasks": total_tasks,
        "completed_tasks": completed_tasks,
        "completion_rate": round(completed_tasks / total_tasks * 100, 1) if total_tasks else 0,
        "total_allocated_min": total_allocated // 60,
        "total_elapsed_min": total_elapsed // 60,
        "total_overrun_min": total_overrun // 60,
        "procrastination_used_min": procrastination_used // 60,
        "procrastination_budget_min": procrastination_budget // 60,
        "daily": daily_stats,
    }


def load_templates() -> list:
    _ensure_dir()
    path = DATA_DIR / "templates.json"
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def save_templates(templates: list):
    _ensure_dir()
    with open(DATA_DIR / "templates.json", "w", encoding="utf-8") as f:
        json.dump(templates, f, ensure_ascii=False, indent=2)


def load_yesterday_unfinished():
    """Возвращает незавершённые/непропущенные задачи вчерашнего дня."""
    from datetime import date, timedelta
    from models import TaskStatus
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    plan = load_day(yesterday)
    return [t for t in plan.tasks
            if t.status in (TaskStatus.PENDING, TaskStatus.ACTIVE)]


def add_task_to_day(day: str, task):
    """Добавляет задачу в план указанного дня (создаёт если нет)."""
    import uuid
    from models import Task, TaskStatus
    plan = load_day(day)
    # Создаём свежую копию без elapsed
    fresh = Task(
        name=task.name,
        allocated_seconds=task.allocated_seconds,
        scheduled_time=task.scheduled_time,
    )
    plan.tasks.append(fresh)
    save_day(plan)


def load_user_presets() -> list:
    _ensure_dir()
    path = DATA_DIR / "presets.json"
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def save_user_presets(presets: list):
    _ensure_dir()
    with open(DATA_DIR / "presets.json", "w", encoding="utf-8") as f:
        json.dump(presets, f, ensure_ascii=False, indent=2)
