import threading
import time
from datetime import datetime, date
from typing import Optional, Callable

from models import Task, DayPlan, TaskStatus, OverrunMode, AppSettings


class TimerEngine:
    """
    Шахматный таймер — идёт ВСЕГДА с момента запуска.
    Нет активной задачи → секунды автоматически идут в прокрастинацию.
    Лимит прокрастинации = 24ч - сумма задач (или override из настроек).
    """

    SECONDS_IN_DAY = 86400

    def __init__(self, plan: DayPlan, settings: AppSettings, on_tick: Optional[Callable] = None):
        self.plan = plan
        self.settings = settings
        self.on_tick = on_tick
        self.active_task_id: Optional[str] = None
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()

    @property
    def procrastination_active(self) -> bool:
        return self._running and self.active_task_id is None

    def procrastination_limit(self) -> int:
        if self.settings.procrastination_override_minutes is not None:
            return self.settings.procrastination_override_minutes * 60
        return max(0, self.SECONDS_IN_DAY - self.plan.total_allocated())

    def procrastination_remaining(self) -> int:
        return max(0, self.procrastination_limit() - self.plan.procrastination_used)

    def procrastination_overrun(self) -> int:
        return max(0, self.plan.procrastination_used - self.procrastination_limit())

    def activate_task(self, task_id: str):
        with self._lock:
            self.active_task_id = task_id
            task = self._get_task(task_id)
            if task and task.status == TaskStatus.PENDING:
                task.status = TaskStatus.ACTIVE

    def deactivate(self):
        with self._lock:
            self.active_task_id = None

    def complete_task(self, task_id: str):
        with self._lock:
            task = self._get_task(task_id)
            if task:
                task.status = TaskStatus.COMPLETED
                task.completed_at = datetime.now().isoformat()
            if self.active_task_id == task_id:
                self.active_task_id = None

    def skip_task(self, task_id: str):
        with self._lock:
            task = self._get_task(task_id)
            if task:
                task.status = TaskStatus.SKIPPED
            if self.active_task_id == task_id:
                self.active_task_id = None

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False

    def _loop(self):
        while self._running:
            time.sleep(1)
            with self._lock:
                self._tick()
            if self.on_tick:
                self.on_tick(self.plan)

    def _tick(self):
        if not self.active_task_id:
            self.plan.procrastination_used += 1
            return

        task = self._get_task(self.active_task_id)
        if not task or task.status in (TaskStatus.COMPLETED, TaskStatus.SKIPPED):
            self.active_task_id = None
            self.plan.procrastination_used += 1
            return

        task.elapsed_seconds += 1

        if task.elapsed_seconds > task.allocated_seconds:
            overrun_delta = task.elapsed_seconds - task.allocated_seconds
            prev_overrun = task.overrun_seconds
            task.overrun_seconds = overrun_delta
            delta = overrun_delta - prev_overrun

            mode = self.settings.overrun_mode
            if mode == OverrunMode.EAT_PROCRASTINATION:
                self.plan.procrastination_used += delta
            elif mode == OverrunMode.EAT_PROPORTIONAL:
                self._eat_proportional(delta)

    def _eat_proportional(self, delta: int):
        pending = [
            t for t in self.plan.tasks
            if t.status in (TaskStatus.PENDING, TaskStatus.ACTIVE)
            and t.id != self.active_task_id
            and t.remaining_seconds > 0
        ]
        if not pending:
            return
        total_remaining = sum(t.remaining_seconds for t in pending)
        for t in pending:
            share = delta * t.remaining_seconds / total_remaining
            t.allocated_seconds = max(0, t.allocated_seconds - int(share))

    def _get_task(self, task_id: str) -> Optional[Task]:
        for t in self.plan.tasks:
            if t.id == task_id:
                return t
        return None


class NotificationScheduler:
    def __init__(self, plan: DayPlan, settings: AppSettings, notify_cb: Optional[Callable] = None):
        self.plan = plan
        self.settings = settings
        self.notify_cb = notify_cb
        self._notified: set = set()
        self._running = False
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
        for task in self.plan.tasks:
            if not task.scheduled_time or task.id in self._notified:
                continue
            if task.status in (TaskStatus.COMPLETED, TaskStatus.SKIPPED):
                continue
            try:
                scheduled = datetime.strptime(
                    f"{date.today().isoformat()} {task.scheduled_time}", "%Y-%m-%d %H:%M"
                )
            except ValueError:
                continue
            seconds_until = (scheduled - now).total_seconds()
            if 0 <= seconds_until <= notify_ahead:
                self._notified.add(task.id)
                title = f"⏰ Скоро: {task.name}"
                mins = int(seconds_until // 60)
                msg = f"Через {mins} мин. ({task.scheduled_time})" if mins > 0 else "Уже сейчас!"
                self._send(title, msg)

    def _send(self, title: str, message: str):
        if self.notify_cb:
            self.notify_cb(title, message)
        try:
            from plyer import notification
            notification.notify(title=title, message=message, timeout=8)
        except Exception:
            pass
