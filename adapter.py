"""
Адаптер между новым репозиторием/engine и старым UI.
UI получает те же dataclass-объекты что и раньше.
"""
from dataclasses import dataclass, field
from datetime import datetime, date
from enum import Enum
from typing import Optional
import uuid

from lt_db import TaskStatus as DBTaskStatus
from lt_db import Priority  # noqa — re-export


# ── Переэкспортируем enums чтобы UI мог импортировать из одного места ──

class TaskStatus(str, Enum):
    PENDING   = "pending"
    ACTIVE    = "active"
    COMPLETED = "completed"
    SKIPPED   = "skipped"


# ── Доменные объекты для UI ──

@dataclass
class Task:
    name: str
    allocated_seconds: int
    id: str                        = field(default_factory=lambda: str(uuid.uuid4()))
    status: TaskStatus             = TaskStatus.PENDING
    scheduled_time: Optional[str]  = None
    elapsed_seconds: int           = 0
    overrun_seconds: int           = 0
    completed_at: Optional[str]    = None
    created_at: str                = field(default_factory=lambda: datetime.now().isoformat())
    priority: "Priority"           = None  # будет Priority.NORMAL после импорта

    def __post_init__(self):
        if self.priority is None:
            from lt_db import Priority
            self.priority = Priority.NORMAL

    @property
    def remaining_seconds(self) -> int:
        return max(0, self.allocated_seconds - self.elapsed_seconds)

    @property
    def is_overrun(self) -> bool:
        return self.elapsed_seconds > self.allocated_seconds


@dataclass
class DayPlan:
    date: str                  = field(default_factory=lambda: date.today().isoformat())
    tasks: list                = field(default_factory=list)
    procrastination_used: int  = 0

    def total_allocated(self) -> int:
        return sum(t.allocated_seconds for t in self.tasks)

    def total_elapsed(self) -> int:
        return sum(t.elapsed_seconds for t in self.tasks)


def engine_to_plan(engine) -> DayPlan:
    """Конвертирует состояние TimerEngine в DayPlan для UI."""
    tasks = []
    for t in engine.get_tasks():
        tasks.append(Task(
            id                = t["id"],
            name              = t["name"],
            allocated_seconds = t["allocated_seconds"],
            elapsed_seconds   = t["elapsed_seconds"],
            overrun_seconds   = t["overrun_seconds"],
            status            = TaskStatus(t["status"].value if hasattr(t["status"], "value") else t["status"]),
            scheduled_time    = t["scheduled_time"],
            completed_at      = t["completed_at"].isoformat() if t["completed_at"] else None,
            priority          = t.get("priority", Priority.NORMAL),
        ))
    return DayPlan(
        date=date.today().isoformat(),
        tasks=tasks,
        procrastination_used=engine.get_proc_used(),
    )


def db_task_to_ui(t) -> Task:
    """Конвертирует SQLAlchemy Task в UI Task."""
    return Task(
        id                = t.id,
        name              = t.name,
        allocated_seconds = t.allocated_seconds,
        elapsed_seconds   = t.elapsed_seconds,
        overrun_seconds   = t.overrun_seconds,
        status            = TaskStatus(t.status.value),
        scheduled_time    = t.scheduled_time,
        completed_at      = t.completed_at.isoformat() if t.completed_at else None,
        priority          = t.priority if hasattr(t, "priority") and t.priority else Priority.NORMAL,
    )

# ── Re-export enums и Settings для совместимости с UI ──

from lt_db import OverrunBehavior, OverrunSource  # noqa

# AppSettings — тонкая обёртка над database.Settings
# UI передаёт его в SettingsDialog и обратно, не зная про SQLAlchemy
class AppSettings:
    """
    Обёртка над database.Settings для UI.
    Поля совпадают с тем что ожидают диалоги.
    """
    def __init__(self, db_settings=None):
        if db_settings:
            self.overrun_behavior               = db_settings.overrun_behavior
            self.overrun_source                 = db_settings.overrun_source
            # UI использует старое имя поля
            self.procrastination_override_minutes = db_settings.procrastination_override_min
            self.notify_before_minutes          = db_settings.notify_before_minutes
            self.theme                          = db_settings.theme
            self.gamification_enabled           = db_settings.gamification_enabled
            self.base_bonus                     = db_settings.base_bonus
            self.base_penalty                   = db_settings.base_penalty
            self.allow_negative_balance         = db_settings.allow_negative_balance
        else:
            self.overrun_behavior               = OverrunBehavior.CONTINUE
            self.overrun_source                 = OverrunSource.PROCRASTINATION
            self.procrastination_override_minutes = None
            self.notify_before_minutes          = 5
            self.theme                          = "dark"
            self.gamification_enabled           = False
            self.base_bonus                     = 10
            self.base_penalty                   = 10
            self.allow_negative_balance         = False

    def to_db_dict(self) -> dict:
        """Конвертирует в словарь для repository.save_settings()"""
        return {
            "overrun_behavior":            self.overrun_behavior,
            "overrun_source":              self.overrun_source,
            "procrastination_override_min": self.procrastination_override_minutes,
            "notify_before_minutes":       self.notify_before_minutes,
            "theme":                       self.theme,
            "gamification_enabled":        self.gamification_enabled,
            "base_bonus":                  self.base_bonus,
            "base_penalty":               self.base_penalty,
            "allow_negative_balance":      self.allow_negative_balance,
        }

