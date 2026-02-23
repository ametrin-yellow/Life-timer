import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

import customtkinter as ctk
from datetime import date, timedelta
from typing import Optional

import storage
from models import DayPlan, AppSettings, Task, TaskStatus
from timer import TimerEngine, NotificationScheduler
from ui.timer_header import TimerHeader
from ui.task_panel import TaskPanel
from ui.add_task_dialog import AddTaskDialog
from ui.stats_panel import StatsPanel
from ui.settings_dialog import SettingsDialog
from ui.templates_dialog import TemplatesDialog
from ui.skip_dialog import SkipDialog
from ui.carry_over_dialog import CarryOverDialog


class LifeTimerApp(ctk.CTk):

    def __init__(self):
        super().__init__()
        self.title("⏱ Life Timer")
        self.geometry("720x620")
        self.minsize(640, 520)

        self.settings: AppSettings = storage.load_settings()
        ctk.set_appearance_mode(self.settings.theme)
        ctk.set_default_color_theme("blue")

        self._current_date: date = date.today()
        self.plan: DayPlan = storage.load_today()
        self.engine = TimerEngine(self.plan, self.settings, on_tick=self._on_tick)
        self.notifier = NotificationScheduler(self.plan, self.settings, notify_cb=self._on_notify)
        self._notification_queue: list[tuple[str, str]] = []

        self._build_ui()
        self.engine.start()
        self.notifier.start()
        self._check_notifications()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        # Проверяем незавершённые вчера — с небольшой задержкой чтобы UI успел отрисоваться
        self.after(800, self._check_carry_over)

    # ──────────────────────────────────────────────
    #  UI
    # ──────────────────────────────────────────────

    def _build_ui(self):
        self.header = TimerHeader(
            self, self.plan,
            active_task_id=self.engine.active_task_id,
            proc_remaining=self.engine.procrastination_remaining(),
            proc_overrun=self.engine.procrastination_overrun(),
            height=120,
        )
        self.header.pack(fill="x", padx=10, pady=(10, 4))

        # Тулбар с навигацией по дням
        self.toolbar = toolbar = ctk.CTkFrame(self, fg_color="transparent")
        toolbar.pack(fill="x", padx=10, pady=2)

        # Навигация — левый блок
        nav = ctk.CTkFrame(toolbar, fg_color="transparent")
        nav.pack(side="left")
        ctk.CTkButton(nav, text="◀", width=32, height=28, corner_radius=6,
                      fg_color="#37474F", command=self._prev_day).pack(side="left", padx=(0, 2))
        self.date_lbl = ctk.CTkLabel(nav, text=self._date_label(),
                                      font=("Helvetica", 12), width=160)
        self.date_lbl.pack(side="left", padx=4)
        self.next_btn = ctk.CTkButton(nav, text="▶", width=32, height=28, corner_radius=6,
                                       fg_color="#37474F", command=self._next_day)
        self.next_btn.pack(side="left", padx=(2, 0))
        self._update_next_btn()

        # Правый блок — статистика и настройки
        ctk.CTkButton(toolbar, text="📊 Статистика", width=110, height=28,
                      fg_color="#37474F", corner_radius=6,
                      command=self._open_stats).pack(side="right", padx=4)
        ctk.CTkButton(toolbar, text="⚙ Настройки", width=100, height=28,
                      fg_color="#37474F", corner_radius=6,
                      command=self._open_settings).pack(side="right", padx=4)

        self.task_panel = TaskPanel(
            self, self.plan,
            active_task_id=self.engine.active_task_id,
            readonly=self._is_readonly(),
            on_activate=self._activate_task,
            on_complete=self._complete_task,
            on_skip=self._ask_skip,
            on_add=self._open_add_task,
            on_copy=self._copy_task,
            on_delete=self._delete_task,
            on_load_templates=self._open_templates,
        )
        self.task_panel.pack(fill="both", expand=True, padx=10, pady=(4, 10))

    def _date_label(self) -> str:
        today = date.today()
        if self._current_date == today:
            return f"📅 Сегодня, {today.strftime('%d.%m')}"
        elif self._current_date == today - timedelta(days=1):
            return f"📅 Вчера, {self._current_date.strftime('%d.%m')}"
        else:
            return f"📅 {self._current_date.strftime('%d.%m.%Y')}"

    def _is_readonly(self) -> bool:
        return self._current_date != date.today()

    def _update_next_btn(self):
        if self._current_date >= date.today():
            self.next_btn.configure(state="disabled", fg_color="#2a2a2a")
        else:
            self.next_btn.configure(state="normal", fg_color="#37474F")

    # ──────────────────────────────────────────────
    #  Навигация по дням
    # ──────────────────────────────────────────────

    def _prev_day(self):
        self._current_date -= timedelta(days=1)
        self._switch_day()

    def _next_day(self):
        if self._current_date < date.today():
            self._current_date += timedelta(days=1)
            self._switch_day()

    def _switch_day(self):
        is_today = self._current_date == date.today()

        if is_today:
            # Возвращаемся к сегодня — берём живой план из engine, не перегружаем с диска
            self.plan = self.engine.plan
        else:
            # Прошлый день — грузим readonly
            self.plan = storage.load_day(self._current_date.isoformat())

        self.date_lbl.configure(text=self._date_label())
        self._update_next_btn()

        # Шапку скрываем/показываем через pack_forget / pack с правильным before=
        if is_today:
            self.header.pack(fill="x", padx=10, pady=(10, 4), before=self.toolbar)
        else:
            self.header.pack_forget()

        self.task_panel.refresh(self.plan, self.engine.active_task_id if is_today else None,
                                readonly=self._is_readonly())

    # ──────────────────────────────────────────────
    #  Тик таймера
    # ──────────────────────────────────────────────

    def _on_tick(self, plan: DayPlan):
        self.after(0, self._refresh_ui)
        elapsed = sum(t.elapsed_seconds for t in plan.tasks)
        if elapsed % 30 == 0:
            self.after(0, lambda: storage.save_day(self.plan if self._is_readonly() else plan))

    def _refresh_ui(self):
        if self._is_readonly():
            return  # не трогаем UI пока смотрим прошлый день
        # Обновляем живой план из engine
        self.plan = self.engine.plan
        self.header.refresh(
            self.plan, self.engine.active_task_id,
            self.engine.procrastination_remaining(),
            self.engine.procrastination_overrun(),
        )
        self.task_panel.refresh(self.plan, self.engine.active_task_id)

    # ──────────────────────────────────────────────
    #  Действия с задачами
    # ──────────────────────────────────────────────

    def _activate_task(self, task_id: Optional[str]):
        if task_id is None:
            self.engine.deactivate()
        else:
            self.engine.activate_task(task_id)
        self._refresh_ui()

    def _complete_task(self, task_id: str):
        self.engine.complete_task(task_id)
        storage.save_day(self.engine.plan)
        self._refresh_ui()

    def _ask_skip(self, task_id: str):
        task = next((t for t in self.plan.tasks if t.id == task_id), None)
        if not task:
            return
        tomorrow = (date.today() + timedelta(days=1)).isoformat()
        SkipDialog(
            self, task.name,
            on_skip=lambda: self._do_skip(task_id),
            on_postpone=lambda: self._skip_and_postpone(task_id, tomorrow),
        )

    def _do_skip(self, task_id: str):
        self.engine.skip_task(task_id)
        storage.save_day(self.engine.plan)
        self._refresh_ui()

    def _skip_and_postpone(self, task_id: str, to_day: str):
        task = next((t for t in self.plan.tasks if t.id == task_id), None)
        if task:
            storage.add_task_to_day(to_day, task)
        self.engine.skip_task(task_id)
        storage.save_day(self.engine.plan)
        self._refresh_ui()

    def _copy_task(self, task_id: str):
        original = next((t for t in self.plan.tasks if t.id == task_id), None)
        if not original:
            return
        copy = Task(
            name=f"{original.name} (копия)",
            allocated_seconds=original.allocated_seconds,
            scheduled_time=original.scheduled_time,
        )
        self.engine.plan.tasks.append(copy)
        storage.save_day(self.engine.plan)
        self.task_panel.refresh(self.engine.plan, self.engine.active_task_id)

    def _delete_task(self, task_id: str):
        self.engine.plan.tasks = [t for t in self.engine.plan.tasks if t.id != task_id]
        if self.engine.active_task_id == task_id:
            self.engine.deactivate()
        storage.save_day(self.engine.plan)
        self.task_panel.refresh(self.engine.plan, self.engine.active_task_id)

    def _open_add_task(self):
        AddTaskDialog(self, on_save=self._add_task)

    def _add_task(self, task: Task):
        self.engine.plan.tasks.append(task)
        storage.save_day(self.engine.plan)
        self.task_panel.refresh(self.engine.plan, self.engine.active_task_id)

    def _open_templates(self):
        TemplatesDialog(self, on_load=self._load_templates)

    def _load_templates(self, tasks: list[Task]):
        self.engine.plan.tasks.extend(tasks)
        storage.save_day(self.engine.plan)
        self.task_panel.refresh(self.engine.plan, self.engine.active_task_id)

    # ──────────────────────────────────────────────
    #  Перенос незавершённых вчера
    # ──────────────────────────────────────────────

    def _check_carry_over(self):
        unfinished = storage.load_yesterday_unfinished()
        if not unfinished:
            return
        CarryOverDialog(self, unfinished, on_confirm=self._carry_over_tasks)

    def _carry_over_tasks(self, tasks: list[Task]):
        for task in tasks:
            self.engine.plan.tasks.append(
                Task(name=task.name, allocated_seconds=task.allocated_seconds,
                     scheduled_time=task.scheduled_time)
            )
        storage.save_day(self.engine.plan)
        self.task_panel.refresh(self.engine.plan, self.engine.active_task_id)

    # ──────────────────────────────────────────────
    #  Настройки / статистика
    # ──────────────────────────────────────────────

    def _open_stats(self):
        StatsPanel(self)

    def _open_settings(self):
        SettingsDialog(self, self.settings, on_save=self._apply_settings)

    def _apply_settings(self, settings: AppSettings):
        self.settings = settings
        self.engine.settings = settings
        self.notifier.settings = settings
        ctk.set_appearance_mode(settings.theme)

    # ──────────────────────────────────────────────
    #  Уведомления
    # ──────────────────────────────────────────────

    def _on_notify(self, title: str, message: str):
        self._notification_queue.append((title, message))

    def _check_notifications(self):
        while self._notification_queue:
            title, msg = self._notification_queue.pop(0)
            from tkinter import messagebox
            messagebox.showinfo(title, msg)
        self.after(5000, self._check_notifications)

    # ──────────────────────────────────────────────
    #  Завершение
    # ──────────────────────────────────────────────

    def _on_close(self):
        self.engine.stop()
        self.notifier.stop()
        storage.save_day(self.engine.plan)
        self.destroy()


if __name__ == "__main__":
    app = LifeTimerApp()
    app.mainloop()
