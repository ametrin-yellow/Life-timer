"""
SQLAlchemy модели и инициализация БД.
SQLite локально → Postgres на сервере (один и тот же код).
"""
from datetime import datetime, date
from sqlalchemy import (
    create_engine, Column, String, Integer, Boolean,
    Float, DateTime, Date, ForeignKey, Enum as SAEnum, Text
)
from sqlalchemy.orm import DeclarativeBase, relationship, Session
import enum
import os

DB_PATH = os.path.expanduser("~/.life_timer/life_timer.db")
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

engine = create_engine(f"sqlite:///{DB_PATH}", echo=False)


class Base(DeclarativeBase):
    pass


# ──────────────────────────────────────────────
#  Enums
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
    SINGLE      = "single"       # разовое
    LIMITED     = "limited"      # лимитированное
    SUBSCRIPTION = "subscription" # абонемент


# ──────────────────────────────────────────────
#  Настройки
# ──────────────────────────────────────────────

class Settings(Base):
    __tablename__ = "settings"

    id                          = Column(Integer, primary_key=True, default=1)
    # Таймер
    overrun_behavior            = Column(SAEnum(OverrunBehavior), default=OverrunBehavior.CONTINUE)
    overrun_source              = Column(SAEnum(OverrunSource), default=OverrunSource.PROCRASTINATION)
    procrastination_override_min = Column(Integer, nullable=True)  # None = авто
    notify_before_minutes       = Column(Integer, default=5)
    theme                       = Column(String, default="dark")
    # Геймификация
    gamification_enabled        = Column(Boolean, default=False)
    base_bonus                  = Column(Integer, default=10)
    base_penalty                = Column(Integer, default=10)
    allow_negative_balance      = Column(Boolean, default=False)


# ──────────────────────────────────────────────
#  Планы и задачи
# ──────────────────────────────────────────────

class DayPlan(Base):
    __tablename__ = "day_plans"

    id                   = Column(Integer, primary_key=True, autoincrement=True)
    date                 = Column(Date, unique=True, nullable=False, index=True)
    procrastination_used = Column(Integer, default=0)  # секунды
    # Геймификация — итоги дня
    day_bonus            = Column(Integer, default=0)
    day_penalty          = Column(Integer, default=0)
    day_total            = Column(Integer, default=0)   # после стрик-множителя
    day_finalized        = Column(Boolean, default=False)

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
    scheduled_time    = Column(String, nullable=True)      # "HH:MM"
    position          = Column(Integer, default=0)         # для сортировки
    created_at        = Column(DateTime, default=datetime.now)
    completed_at      = Column(DateTime, nullable=True)
    # Приоритет
    priority          = Column(SAEnum(Priority, values_callable=lambda e: [x.value for x in e]),
                              default=Priority.NORMAL)
    # Геймификация
    coins_earned      = Column(Integer, default=0)
    coins_penalty     = Column(Integer, default=0)

    plan = relationship("DayPlan", back_populates="tasks")


# ──────────────────────────────────────────────
#  Геймификация — баланс и история
# ──────────────────────────────────────────────

class CoinBalance(Base):
    __tablename__ = "coin_balance"

    id      = Column(Integer, primary_key=True, default=1)
    balance = Column(Integer, default=0)
    streak  = Column(Integer, default=0)   # текущая серия бесштрафных дней


class CoinTransaction(Base):
    __tablename__ = "coin_transactions"

    id          = Column(Integer, primary_key=True, autoincrement=True)
    created_at  = Column(DateTime, default=datetime.now)
    amount      = Column(Integer, nullable=False)  # + бонус, - штраф/покупка
    reason      = Column(String, nullable=False)   # human-readable описание
    task_id     = Column(String, ForeignKey("tasks.id"), nullable=True)
    plan_date   = Column(Date, nullable=True)
    reward_id   = Column(Integer, ForeignKey("rewards.id"), nullable=True)


# ──────────────────────────────────────────────
#  Магазин
# ──────────────────────────────────────────────

class Reward(Base):
    __tablename__ = "rewards"

    id            = Column(Integer, primary_key=True, autoincrement=True)
    name          = Column(String, nullable=False)
    description   = Column(Text, nullable=True)
    price         = Column(Integer, nullable=False)        # в коинах
    reward_type   = Column(SAEnum(RewardType), nullable=False)
    count         = Column(Integer, nullable=True)         # для LIMITED: остаток
    count_initial = Column(Integer, nullable=True)         # для LIMITED: начальное
    is_active     = Column(Boolean, default=True)
    created_at    = Column(DateTime, default=datetime.now)


# ──────────────────────────────────────────────
#  Шаблоны и пресеты
# ──────────────────────────────────────────────

class Template(Base):
    __tablename__ = "templates"

    id                = Column(Integer, primary_key=True, autoincrement=True)
    name              = Column(String, nullable=False)
    allocated_seconds = Column(Integer, nullable=False)
    category          = Column(String, nullable=False, default="👤 Мои шаблоны")
    is_builtin        = Column(Boolean, default=False)


class Preset(Base):
    __tablename__ = "presets"

    id         = Column(Integer, primary_key=True, autoincrement=True)
    name       = Column(String, nullable=False)
    is_builtin = Column(Boolean, default=False)

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


# ──────────────────────────────────────────────
#  Инициализация
# ──────────────────────────────────────────────

def init_db():
    """Создаём таблицы и заполняем встроенные шаблоны/пресеты/настройки."""
    Base.metadata.create_all(engine)
    _migrate(engine)
    with Session(engine) as s:
        _seed_settings(s)
        _seed_templates(s)
        _seed_presets(s)
        _seed_balance(s)
        s.commit()


def _migrate(eng):
    """
    Мягкие миграции — добавляем колонки которых нет.
    Безопасно: каждая операция проверяет наличие колонки перед ALTER TABLE.
    """
    with eng.connect() as conn:
        _add_column_if_missing(conn, "tasks", "priority",
                               "VARCHAR DEFAULT 'normal'")


def _add_column_if_missing(conn, table: str, column: str, col_def: str):
    """ALTER TABLE только если колонки ещё нет."""
    from sqlalchemy import text
    result = conn.execute(text(f"PRAGMA table_info({table})"))
    existing = {row[1] for row in result}
    if column not in existing:
        conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {col_def}"))
        conn.commit()


def get_session() -> Session:
    return Session(engine)


def _seed_settings(s: Session):
    if not s.get(Settings, 1):
        s.add(Settings(id=1))


def _seed_balance(s: Session):
    if not s.get(CoinBalance, 1):
        s.add(CoinBalance(id=1))


def _seed_templates(s: Session):
    if s.query(Template).filter_by(is_builtin=True).count():
        return
    builtins = [
        ("🌙 Сон и отдых",  "Сон",             480 * 60),
        ("🌙 Сон и отдых",  "Дневной сон",      30 * 60),
        ("🚿 Гигиена",      "Утренние ритуалы", 30 * 60),
        ("🚿 Гигиена",      "Вечерние ритуалы", 20 * 60),
        ("🍳 Еда",          "Завтрак",          20 * 60),
        ("🍳 Еда",          "Обед",             30 * 60),
        ("🍳 Еда",          "Ужин",             30 * 60),
        ("🍳 Еда",          "Готовка",          45 * 60),
        ("🏃 Активность",   "Зарядка",          15 * 60),
        ("🏃 Активность",   "Спорт",            60 * 60),
        ("🏃 Активность",   "Прогулка",         45 * 60),
        ("🧘 Ментальное",   "Медитация",        15 * 60),
        ("🧘 Ментальное",   "Планирование дня", 15 * 60),
        ("🧘 Ментальное",   "Дневник",          15 * 60),
        ("🏠 Быт",          "Уборка",           30 * 60),
        ("🏠 Быт",          "Покупки",          45 * 60),
    ]
    for cat, name, secs in builtins:
        s.add(Template(name=name, allocated_seconds=secs,
                       category=cat, is_builtin=True))
    s.flush()


def _seed_presets(s: Session):
    if s.query(Preset).filter_by(is_builtin=True).count():
        return

    def tmpl(name):
        return s.query(Template).filter_by(name=name, is_builtin=True).first()

    presets_data = {
        "💼 Рабочий день": [
            "Сон", "Утренние ритуалы", "Завтрак",
            "Обед", "Ужин", "Вечерние ритуалы",
        ],
        "🛋 Выходной": [
            "Сон", "Утренние ритуалы", "Завтрак",
            "Прогулка", "Обед", "Дневной сон",
            "Ужин", "Вечерние ритуалы",
        ],
    }
    for preset_name, template_names in presets_data.items():
        p = Preset(name=preset_name, is_builtin=True)
        s.add(p)
        s.flush()
        for i, tname in enumerate(template_names):
            t = tmpl(tname)
            if t:
                s.add(PresetItem(preset_id=p.id, template_id=t.id, position=i))
