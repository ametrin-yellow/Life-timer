from dataclasses import dataclass, field
from datetime import datetime, date
from enum import Enum
from typing import Optional
import uuid


class OverrunMode(Enum):
    MINUS = "minus"
    EAT_PROCRASTINATION = "eat_procrastination"
    EAT_PROPORTIONAL = "eat_proportional"


class TaskStatus(Enum):
    PENDING = "pending"
    ACTIVE = "active"
    COMPLETED = "completed"
    SKIPPED = "skipped"


@dataclass
class Task:
    name: str
    allocated_seconds: int
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    status: TaskStatus = TaskStatus.PENDING
    scheduled_time: Optional[str] = None   # "HH:MM" или None — опционально
    elapsed_seconds: int = 0
    overrun_seconds: int = 0
    completed_at: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    @property
    def remaining_seconds(self) -> int:
        return max(0, self.allocated_seconds - self.elapsed_seconds)

    @property
    def is_overrun(self) -> bool:
        return self.elapsed_seconds > self.allocated_seconds

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "allocated_seconds": self.allocated_seconds,
            "status": self.status.value,
            "scheduled_time": self.scheduled_time,
            "elapsed_seconds": self.elapsed_seconds,
            "overrun_seconds": self.overrun_seconds,
            "completed_at": self.completed_at,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Task":
        t = cls(
            name=d["name"],
            allocated_seconds=d["allocated_seconds"],
            id=d["id"],
            scheduled_time=d.get("scheduled_time"),
            elapsed_seconds=d.get("elapsed_seconds", 0),
            overrun_seconds=d.get("overrun_seconds", 0),
            completed_at=d.get("completed_at"),
            created_at=d.get("created_at", datetime.now().isoformat()),
        )
        t.status = TaskStatus(d.get("status", "pending"))
        return t


@dataclass
class DayPlan:
    date: str = field(default_factory=lambda: date.today().isoformat())
    tasks: list = field(default_factory=list)
    procrastination_used: int = 0   # накопленные секунды прокрастинации

    def total_allocated(self) -> int:
        return sum(t.allocated_seconds for t in self.tasks)

    def total_elapsed(self) -> int:
        return sum(t.elapsed_seconds for t in self.tasks)

    def total_overrun(self) -> int:
        return sum(t.overrun_seconds for t in self.tasks)

    def to_dict(self) -> dict:
        return {
            "date": self.date,
            "tasks": [t.to_dict() for t in self.tasks],
            "procrastination_used": self.procrastination_used,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "DayPlan":
        plan = cls(
            date=d["date"],
            procrastination_used=d.get("procrastination_used", 0),
        )
        plan.tasks = [Task.from_dict(t) for t in d.get("tasks", [])]
        return plan


@dataclass
class AppSettings:
    overrun_mode: OverrunMode = OverrunMode.EAT_PROCRASTINATION
    # None = автоматически (24ч - задачи), число = ручной override в минутах
    procrastination_override_minutes: Optional[int] = None
    notify_before_minutes: int = 5
    theme: str = "dark"

    def to_dict(self) -> dict:
        return {
            "overrun_mode": self.overrun_mode.value,
            "procrastination_override_minutes": self.procrastination_override_minutes,
            "notify_before_minutes": self.notify_before_minutes,
            "theme": self.theme,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "AppSettings":
        s = cls()
        if "overrun_mode" in d:
            s.overrun_mode = OverrunMode(d["overrun_mode"])
        s.procrastination_override_minutes = d.get("procrastination_override_minutes")
        s.notify_before_minutes = d.get("notify_before_minutes", 5)
        s.theme = d.get("theme", "dark")
        return s
