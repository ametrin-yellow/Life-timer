"""
Pydantic схемы — request/response для всех роутеров.
Отдельный файл чтобы не засорять роутеры и не дублировать.
"""
from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, field_validator

from models import TaskStatus, Priority, OverrunBehavior, OverrunSource, RewardType


# ──────────────────────────────────────────────
#  Tasks
# ──────────────────────────────────────────────

class TaskCreate(BaseModel):
    name: str
    allocated_seconds: int
    scheduled_time: Optional[str] = None   # "HH:MM"
    position: int = 0
    priority: Priority = Priority.NORMAL

    @field_validator("allocated_seconds")
    @classmethod
    def positive_seconds(cls, v):
        if v <= 0:
            raise ValueError("allocated_seconds должен быть > 0")
        return v


class TaskUpdate(BaseModel):
    name: Optional[str] = None
    allocated_seconds: Optional[int] = None
    scheduled_time: Optional[str] = None
    position: Optional[int] = None
    priority: Optional[Priority] = None
    elapsed_seconds: Optional[int] = None
    overrun_seconds: Optional[int] = None
    status: Optional[TaskStatus] = None
    completed_at: Optional[datetime] = None
    coins_earned: Optional[int] = None
    coins_penalty: Optional[int] = None


class TaskResponse(BaseModel):
    id: str
    plan_id: int
    name: str
    allocated_seconds: int
    elapsed_seconds: int
    overrun_seconds: int
    status: TaskStatus
    scheduled_time: Optional[str]
    position: int
    priority: Priority
    coins_earned: int
    coins_penalty: int
    created_at: datetime
    completed_at: Optional[datetime]

    model_config = {"from_attributes": True}


# ──────────────────────────────────────────────
#  Plans
# ──────────────────────────────────────────────

class PlanResponse(BaseModel):
    id: int
    date: date
    procrastination_used: int
    day_bonus: int
    day_penalty: int
    day_total: int
    day_finalized: bool
    tasks: list[TaskResponse] = []

    model_config = {"from_attributes": True}


class PlanUpdate(BaseModel):
    procrastination_used: Optional[int] = None
    day_bonus: Optional[int] = None
    day_penalty: Optional[int] = None
    day_total: Optional[int] = None
    day_finalized: Optional[bool] = None


# ──────────────────────────────────────────────
#  Settings
# ──────────────────────────────────────────────

class SettingsResponse(BaseModel):
    overrun_behavior: OverrunBehavior
    overrun_source: OverrunSource
    procrastination_override_min: Optional[int]
    notify_before_minutes: int
    theme: str
    gamification_enabled: bool
    base_bonus: int
    base_penalty: int
    allow_negative_balance: bool

    model_config = {"from_attributes": True}


class SettingsUpdate(BaseModel):
    overrun_behavior: Optional[OverrunBehavior] = None
    overrun_source: Optional[OverrunSource] = None
    procrastination_override_min: Optional[int] = None
    notify_before_minutes: Optional[int] = None
    theme: Optional[str] = None
    gamification_enabled: Optional[bool] = None
    base_bonus: Optional[int] = None
    base_penalty: Optional[int] = None
    allow_negative_balance: Optional[bool] = None


# ──────────────────────────────────────────────
#  Gamification
# ──────────────────────────────────────────────

class CoinBalanceResponse(BaseModel):
    balance: int
    streak: int

    model_config = {"from_attributes": True}


class CoinTransactionResponse(BaseModel):
    id: int
    created_at: datetime
    amount: int
    reason: str
    task_id: Optional[str]
    plan_date: Optional[date]
    reward_id: Optional[int]

    model_config = {"from_attributes": True}


# ──────────────────────────────────────────────
#  Shop
# ──────────────────────────────────────────────

class RewardCreate(BaseModel):
    name: str
    price: int
    reward_type: RewardType
    description: Optional[str] = None
    count: Optional[int] = None


class RewardUpdate(BaseModel):
    name: Optional[str] = None
    price: Optional[int] = None
    description: Optional[str] = None
    count_add: int = 0


class RewardResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    price: int
    reward_type: RewardType
    count: Optional[int]
    count_initial: Optional[int]
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# ──────────────────────────────────────────────
#  Events
# ──────────────────────────────────────────────

from models import EventType

class EventIn(BaseModel):
    device_id:   str
    event_type:  EventType
    payload:     dict
    occurred_at: datetime


class EventBatchIn(BaseModel):
    events: list[EventIn]


class EventResponse(BaseModel):
    id:          int
    device_id:   str
    event_type:  EventType
    payload:     dict
    occurred_at: datetime
    received_at: datetime

    model_config = {"from_attributes": True}