import threading
import time
from datetime import datetime, date
from typing import Optional, Callable

from lt_db import TaskStatus, OverrunBehavior, OverrunSource, Settings
import repository as repo


class TimerEngine:
    """
    Шахматный таймер — идёт ВСЕГДА.
    Нет активной задачи → секунды идут в прокрастинацию.
    Работает с plan_id, обновляет БД каждые N секунд.
    """

    SECONDS_IN_DAY = 86400
    SAVE_INTERVAL  = 10  # flush в БД каждые 10 секунд

    def __init__(self, plan_id: int, settings: Settings,
                 on_tick: Optional[Callable] = None):
        self.plan_id        = plan_id
        self.settings       = settings
        self.on_tick        = on_tick
        self.active_task_id: Optional[str] = None

        # In-memory состояние (синхронизируется с БД периодически)
        self._tasks: dict = {}         # task_id → dict с полями
        self._proc_used: int = 0
        self._dirty_ticks: int = 0

        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()

        self._load_state()

    # ──────────────────────────────────────────────
    #  Загрузка / сохранение
    # ──────────────────────────────────────────────

    def _load_state(self):
        tasks = repo.get_tasks_for_plan(self.plan_id)
        plan  = repo.get_plan_with_tasks(self._current_date())
        self._proc_used = plan.procrastination_used if plan else 0
        self._tasks = {
            t.id: {
                "id":                t.id,
                "name":              t.name,
                "allocated_seconds": t.allocated_seconds,
                "elapsed_seconds":   t.elapsed_seconds,
                "overrun_seconds":   t.overrun_seconds,
                "status":            t.status,
                "scheduled_time":    t.scheduled_time,
                "completed_at":      t.completed_at,
                "priority":          t.priority if hasattr(t, "priority") and t.priority else None,
            }
            for t in tasks
        }

    def _flush(self):
        """Записывает накопленные изменения в БД."""
        repo.update_plan(self.plan_id, procrastination_used=self._proc_used)
        for t in self._tasks.values():
            repo.update_task(t["id"],
                             elapsed_seconds=t["elapsed_seconds"],
                             overrun_seconds=t["overrun_seconds"],
                             status=t["status"],
                             completed_at=t["completed_at"])

    def _current_date(self):
        return date.today()

    # ──────────────────────────────────────────────
    #  Публичные свойства
    # ──────────────────────────────────────────────

    @property
    def procrastination_active(self) -> bool:
        return self._running and self.active_task_id is None

    def procrastination_limit(self) -> int:
        """Теоретический максимум прокрастинации за весь день (24ч - все задачи)."""
        if self.settings.procrastination_override_minutes is not None:
            return self.settings.procrastination_override_minutes * 60
        tasks_time = sum(
            t["elapsed_seconds"]
            if t["status"] in (TaskStatus.COMPLETED, TaskStatus.SKIPPED)
            else t["allocated_seconds"]
            for t in self._tasks.values()
        )
        return max(0, self.SECONDS_IN_DAY - tasks_time)

    def procrastination_remaining(self) -> int:
        """
        Сколько прокрастинации осталось с учётом реального времени суток.
        remaining = (секунд до полуночи) - (время незавершённых задач)
        """
        now = datetime.now()
        midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
        seconds_until_midnight = self.SECONDS_IN_DAY - int((now - midnight).total_seconds())

        pending_tasks_time = sum(
            t["allocated_seconds"]
            for t in self._tasks.values()
            if t["status"] not in (TaskStatus.COMPLETED, TaskStatus.SKIPPED)
        )
        return max(0, seconds_until_midnight - pending_tasks_time)

    def procrastination_overrun(self) -> int:
        return max(0, self._proc_used - self.procrastination_limit())

    def get_tasks(self) -> list[dict]:
        return list(self._tasks.values())

    def get_task(self, task_id: str) -> Optional[dict]:
        return self._tasks.get(task_id)

    def get_proc_used(self) -> int:
        return self._proc_used

    # ──────────────────────────────────────────────
    #  Управление задачами
    # ──────────────────────────────────────────────

    def add_task(self, task_id: str, name: str, allocated_seconds: int,
                 scheduled_time: Optional[str] = None, priority=None):
        with self._lock:
            from lt_db import Priority
            self._tasks[task_id] = {
                "id": task_id,
                "name": name,
                "allocated_seconds": allocated_seconds,
                "elapsed_seconds": 0,
                "overrun_seconds": 0,
                "status": TaskStatus.PENDING,
                "scheduled_time": scheduled_time,
                "completed_at": None,
                "priority": priority or Priority.NORMAL,
            }

    def remove_task(self, task_id: str):
        with self._lock:
            self._tasks.pop(task_id, None)
            if self.active_task_id == task_id:
                self.active_task_id = None

    def update_task_meta(self, task_id: str, name: str,
                         allocated_seconds: int, scheduled_time: Optional[str],
                         priority=None):
        """Обновить название/время/приоритет задачи без сброса elapsed."""
        with self._lock:
            if task_id in self._tasks:
                self._tasks[task_id]["name"] = name
                self._tasks[task_id]["allocated_seconds"] = allocated_seconds
                self._tasks[task_id]["scheduled_time"] = scheduled_time
                if priority is not None:
                    self._tasks[task_id]["priority"] = priority

    def activate_task(self, task_id: str):
        with self._lock:
            self.active_task_id = task_id
            if task_id in self._tasks:
                t = self._tasks[task_id]
                if t["status"] == TaskStatus.PENDING:
                    t["status"] = TaskStatus.ACTIVE

    def deactivate(self):
        with self._lock:
            self.active_task_id = None

    def complete_task(self, task_id: str):
        with self._lock:
            if task_id in self._tasks:
                self._tasks[task_id]["status"] = TaskStatus.COMPLETED
                self._tasks[task_id]["completed_at"] = datetime.now()
            if self.active_task_id == task_id:
                self.active_task_id = None
        self._flush()

    def skip_task(self, task_id: str):
        with self._lock:
            if task_id in self._tasks:
                self._tasks[task_id]["status"] = TaskStatus.SKIPPED
                self._tasks[task_id]["completed_at"] = datetime.now()
            if self.active_task_id == task_id:
                self.active_task_id = None
        self._flush()

    # ──────────────────────────────────────────────
    #  Основной цикл
    # ──────────────────────────────────────────────

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        self._flush()

    def _loop(self):
        while self._running:
            time.sleep(1)
            with self._lock:
                self._tick()
                self._dirty_ticks += 1
                if self._dirty_ticks >= self.SAVE_INTERVAL:
                    self._flush()
                    self._dirty_ticks = 0
            if self.on_tick:
                self.on_tick()

    def _tick(self):
        if not self.active_task_id:
            self._proc_used += 1
            return

        t = self._tasks.get(self.active_task_id)
        if not t or t["status"] in (TaskStatus.COMPLETED, TaskStatus.SKIPPED):
            self.active_task_id = None
            self._proc_used += 1
            return

        t["elapsed_seconds"] += 1

        if t["elapsed_seconds"] > t["allocated_seconds"]:
            if self.settings.overrun_behavior == OverrunBehavior.STOP:
                t["elapsed_seconds"] -= 1
                self.active_task_id = None
                self._proc_used += 1
                return

            overrun_delta = t["elapsed_seconds"] - t["allocated_seconds"]
            prev_overrun  = t["overrun_seconds"]
            t["overrun_seconds"] = overrun_delta
            delta = overrun_delta - prev_overrun

            if self.settings.overrun_source == OverrunSource.PROCRASTINATION:
                self._proc_used += delta
            elif self.settings.overrun_source == OverrunSource.PROPORTIONAL:
                self._eat_proportional(delta)

    def _eat_proportional(self, delta: int):
        pending = [
            t for t in self._tasks.values()
            if t["status"] in (TaskStatus.PENDING, TaskStatus.ACTIVE)
            and t["id"] != self.active_task_id
            and (t["allocated_seconds"] - t["elapsed_seconds"]) > 0
        ]
        if not pending:
            return
        total_remaining = sum(
            t["allocated_seconds"] - t["elapsed_seconds"] for t in pending
        )
        for t in pending:
            share = delta * (t["allocated_seconds"] - t["elapsed_seconds"]) / total_remaining
            t["allocated_seconds"] = max(0, t["allocated_seconds"] - int(share))


class NotificationScheduler:
    def __init__(self, engine: TimerEngine, settings: Settings,
                 notify_cb: Optional[Callable] = None):
        self.engine    = engine
        self.settings  = settings
        self.notify_cb = notify_cb
        self._notified: set = set()
        self._running  = False
        self._thread: Optional[threading.Thread] = None

    def start(self):
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False

    def _loop(self):
        while self._running:
            self._check()
            time.sleep(30)

    def _check(self):
        now = datetime.now()
        notify_ahead = self.settings.notify_before_minutes * 60
        for t in self.engine.get_tasks():
            if not t["scheduled_time"] or t["id"] in self._notified:
                continue
            if t["status"] in (TaskStatus.COMPLETED, TaskStatus.SKIPPED):
                continue
            try:
                scheduled = datetime.strptime(
                    f"{date.today().isoformat()} {t['scheduled_time']}",
                    "%Y-%m-%d %H:%M"
                )
            except ValueError:
                continue
            seconds_until = (scheduled - now).total_seconds()
            if 0 <= seconds_until <= notify_ahead:
                self._notified.add(t["id"])
                mins  = int(seconds_until // 60)
                title = f"⏰ Скоро: {t['name']}"
                msg   = f"Через {mins} мин. ({t['scheduled_time']})" if mins > 0 else "Уже сейчас!"
                self._send(title, msg)

    def _send(self, title: str, message: str):
        if self.notify_cb:
            self.notify_cb(title, message)
        try:
            from plyer import notification
            notification.notify(title=title, message=message, timeout=8)
        except Exception:
            pass
