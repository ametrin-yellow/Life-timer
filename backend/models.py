"""
SQLAlchemy модели для Postgres.
Основа — lt_db.py десктопного клиента.
Ключевые отличия:
  - добавлен User (аутентификация)
  - у DayPlan, Settings, CoinBalance, Reward, Template, Preset → user_id
  - убран SQLite-специфичный код (PRAGMA, движок)
  - id везде Integer autoincrement или UUID String
"""
import enum
from datetime import datetime, date, timezone

from sqlalchemy import (
    Column, String, Integer, Boolean, Float,
    DateTime, Date, ForeignKey, Text,
    Enum as SAEnum, UniqueConstraint,
)
from sqlalchemy.orm import relationship

from database import Base


def _utcnow():
    return datetime.now(timezone.utc)


# ──────────────────────────────────────────────
#  Enums  (те же что в lt_db.py)
# ──────────────────────────────────────────────

class TaskStatus(str, enum.Enum):
    PENDING   = "pending"
    ACTIVE    = "active"
    COMPLETED = "completed"
    SKIPPED   = "skipped"


class OverrunBehavior(str, enum.Enum):
    CONTINUE = "continue"
    STOP     = "stop"


class OverrunSource(str, enum.Enum):
    PROCRASTINATION = "procrastination"
    PROPORTIONAL    = "proportional"


class Priority(str, enum.Enum):
    HIGH   = "high"
    NORMAL = "normal"
    LOW    = "low"


class RewardType(str, enum.Enum):
    SINGLE       = "single"
    LIMITED      = "limited"
    SUBSCRIPTION = "subscription"


# ──────────────────────────────────────────────
#  User
# ──────────────────────────────────────────────

class User(Base):
    __tablename__ = "users"

    id            = Column(Integer, primary_key=True, autoincrement=True)
    email         = Column(String, unique=True, nullable=False, index=True)
    hashed_password = Column(String, nullable=True)
    google_id     = Column(String, unique=True, nullable=True, index=True)
    telegram_id   = Column(String, unique=True, nullable=True, index=True)
    created_at    = Column(DateTime(timezone=True), default=_utcnow)
    is_active     = Column(Boolean, default=True)

    # relations
    settings      = relationship("UserSettings", back_populates="user", uselist=False,
                                 cascade="all, delete-orphan")
    day_plans     = relationship("DayPlan", back_populates="user",
                                 cascade="all, delete-orphan")
    coin_balance  = relationship("CoinBalance", back_populates="user", uselist=False,
                                 cascade="all, delete-orphan")
    rewards       = relationship("Reward", back_populates="user",
                                 cascade="all, delete-orphan")
    templates     = relationship("Template", back_populates="user",
                                 cascade="all, delete-orphan")
    presets       = relationship("Preset", back_populates="user",
                                 cascade="all, delete-orphan")


# ──────────────────────────────────────────────
#  Настройки пользователя
# ──────────────────────────────────────────────

class UserSettings(Base):
    __tablename__ = "user_settings"

    id                           = Column(Integer, primary_key=True, autoincrement=True)
    user_id                      = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    overrun_behavior             = Column(SAEnum(OverrunBehavior), default=OverrunBehavior.CONTINUE)
    overrun_source               = Column(SAEnum(OverrunSource), default=OverrunSource.PROCRASTINATION)
    procrastination_override_min = Column(Integer, nullable=True)
    notify_before_minutes        = Column(Integer, default=5)
    theme                        = Column(String, default="dark")
    gamification_enabled         = Column(Boolean, default=False)
    base_bonus                   = Column(Integer, default=10)
    base_penalty                 = Column(Integer, default=10)
    allow_negative_balance       = Column(Boolean, default=False)
    day_start_hour               = Column(Integer, default=0)

    user = relationship("User", back_populates="settings")


# ──────────────────────────────────────────────
#  Планы и задачи
# ──────────────────────────────────────────────

class DayPlan(Base):
    __tablename__ = "day_plans"
    __table_args__ = (
        UniqueConstraint("user_id", "date", name="uq_user_date"),
    )

    id                   = Column(Integer, primary_key=True, autoincrement=True)
    user_id              = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    date                 = Column(Date, nullable=False, index=True)
    procrastination_used       = Column(Integer, default=0)
    procrastination_started_at = Column(DateTime(timezone=True), nullable=True)
    day_bonus                  = Column(Integer, default=0)
    day_penalty                = Column(Integer, default=0)
    day_total                  = Column(Integer, default=0)
    day_finalized              = Column(Boolean, default=False)

    user  = relationship("User", back_populates="day_plans")
    tasks = relationship("Task", back_populates="plan",
                         cascade="all, delete-orphan", order_by="Task.position")


class Task(Base):
    __tablename__ = "tasks"

    id                = Column(String, primary_key=True)   # uuid
    plan_id           = Column(Integer, ForeignKey("day_plans.id"), nullable=False)
    name              = Column(String, nullable=False)
    allocated_seconds = Column(Integer, nullable=False)
    elapsed_seconds   = Column(Integer, default=0)
    overrun_seconds   = Column(Integer, default=0)
    status            = Column(SAEnum(TaskStatus), default=TaskStatus.PENDING)
    scheduled_time    = Column(String, nullable=True)
    position          = Column(Integer, default=0)
    priority          = Column(SAEnum(Priority), default=Priority.NORMAL)
    is_recurring      = Column(Boolean, default=False)
    coins_earned      = Column(Integer, default=0)
    coins_penalty     = Column(Integer, default=0)
    started_at        = Column(DateTime(timezone=True), nullable=True)
    created_at        = Column(DateTime(timezone=True), default=_utcnow)
    completed_at      = Column(DateTime(timezone=True), nullable=True)

    plan = relationship("DayPlan", back_populates="tasks")


# ──────────────────────────────────────────────
#  Геймификация
# ──────────────────────────────────────────────

class CoinBalance(Base):
    __tablename__ = "coin_balance"

    id      = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    balance = Column(Integer, default=0)
    streak  = Column(Integer, default=0)

    user = relationship("User", back_populates="coin_balance")


class CoinTransaction(Base):
    __tablename__ = "coin_transactions"

    id         = Column(Integer, primary_key=True, autoincrement=True)
    user_id    = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow)
    amount     = Column(Integer, nullable=False)
    reason     = Column(String, nullable=False)
    task_id    = Column(String, ForeignKey("tasks.id"), nullable=True)
    plan_date  = Column(Date, nullable=True)
    reward_id  = Column(Integer, ForeignKey("rewards.id"), nullable=True)


# ──────────────────────────────────────────────
#  Магазин
# ──────────────────────────────────────────────

class Reward(Base):
    __tablename__ = "rewards"

    id            = Column(Integer, primary_key=True, autoincrement=True)
    user_id       = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    name          = Column(String, nullable=False)
    description   = Column(Text, nullable=True)
    price         = Column(Integer, nullable=False)
    reward_type   = Column(SAEnum(RewardType), nullable=False)
    count         = Column(Integer, nullable=True)
    count_initial = Column(Integer, nullable=True)
    is_active     = Column(Boolean, default=True)
    created_at    = Column(DateTime(timezone=True), default=_utcnow)

    user = relationship("User", back_populates="rewards")


# ──────────────────────────────────────────────
#  Шаблоны и пресеты
# ──────────────────────────────────────────────

class Template(Base):
    __tablename__ = "templates"

    id                = Column(Integer, primary_key=True, autoincrement=True)
    user_id           = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    name              = Column(String, nullable=False)
    allocated_seconds = Column(Integer, nullable=False)
    category          = Column(String, nullable=False, default="👤 Мои шаблоны")
    is_builtin        = Column(Boolean, default=False)

    user = relationship("User", back_populates="templates")


class Preset(Base):
    __tablename__ = "presets"

    id         = Column(Integer, primary_key=True, autoincrement=True)
    user_id    = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    name       = Column(String, nullable=False)
    is_builtin = Column(Boolean, default=False)

    user  = relationship("User", back_populates="presets")
    items = relationship("PresetItem", back_populates="preset",
                         cascade="all, delete-orphan", order_by="PresetItem.position")


class PresetItem(Base):
    __tablename__ = "preset_items"

    id          = Column(Integer, primary_key=True, autoincrement=True)
    preset_id   = Column(Integer, ForeignKey("presets.id"), nullable=False)
    template_id = Column(Integer, ForeignKey("templates.id"), nullable=False)
    position    = Column(Integer, default=0)

    preset   = relationship("Preset", back_populates="items")
    template = relationship("Template")


