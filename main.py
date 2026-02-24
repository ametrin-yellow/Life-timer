import sys, os
sys.path.insert(0, os.path.dirname(__file__))

import customtkinter as ctk
from datetime import date, timedelta, datetime
from typing import Optional
import uuid
import threading

from lt_db import init_db, TaskStatus as DBTaskStatus
import repository as repo
import gamification as gami
from adapter import Task, DayPlan, TaskStatus, AppSettings, engine_to_plan, db_task_to_ui
from timer import TimerEngine, NotificationScheduler
from ui.timer_header import TimerHeader
from ui.task_panel import TaskPanel
from ui.add_task_dialog import AddTaskDialog
from ui.stats_panel import StatsPanel
from ui.settings_dialog import SettingsDialog
from ui.templates_dialog import TemplatesDialog
from ui.skip_dialog import SkipDialog
from ui.carry_over_dialog import CarryOverDialog
from ui.edit_task_dialog import EditTaskDialog
from ui.shop_dialog import ShopDialog


class LifeTimerApp(ctk.CTk):

    def __init__(self):
        super().__init__()
        self.title("⏱ Life Timer")
        self.geometry("720x620")
        self.minsize(640, 520)

        init_db()

        self.settings = AppSettings(repo.get_settings())
        ctk.set_appearance_mode(self.settings.theme)
        ctk.set_default_color_theme("blue")

        self._current_date: date = date.today()
        self._today_plan_id: int = repo.get_or_create_plan(date.today()).id

        self.engine = TimerEngine(
            self._today_plan_id, self.settings, on_tick=self._on_tick
        )
        self.notifier = NotificationScheduler(
            self.engine, self.settings, notify_cb=self._on_notify
        )
        self._notification_queue: list = []
        self._ui_plan: DayPlan = engine_to_plan(self.engine)

        self._build_ui()
        self.engine.start()
        self.notifier.start()
        self._check_notifications()
        self._schedule_midnight_check()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.after(800, self._check_carry_over)

    # ──────────────────────────────────────────────
    #  UI
    # ──────────────────────────────────────────────

    def _build_ui(self):
        settings = repo.get_settings()
        self._gamification_enabled = settings.gamification_enabled
        coin_bal, coin_streak = self._get_coin_state()

        self.header = TimerHeader(
            self, self._ui_plan,
            active_task_id=self.engine.active_task_id,
            proc_remaining=self.engine.procrastination_remaining(),
            proc_overrun=self.engine.procrastination_overrun(),
            gamification_enabled=self._gamification_enabled,
            coin_balance=coin_bal,
            coin_streak=coin_streak,
            height=120,
        )
        self.header.pack(fill="x", padx=10, pady=(10, 4))

        self.toolbar = toolbar = ctk.CTkFrame(self, fg_color="transparent")
        toolbar.pack(fill="x", padx=10, pady=2)

        nav = ctk.CTkFrame(toolbar, fg_color="transparent")
        nav.pack(side="left")
        ctk.CTkButton(nav, text="◀", width=32, height=28, corner_radius=6,
                      fg_color="#37474F", command=self._prev_day).pack(side="left", padx=(0,2))
        self.date_lbl = ctk.CTkLabel(nav, text=self._date_label(),
                                      font=("Helvetica", 12), width=160)
        self.date_lbl.pack(side="left", padx=4)
        self.next_btn = ctk.CTkButton(nav, text="▶", width=32, height=28, corner_radius=6,
                                       fg_color="#37474F", command=self._next_day)
        self.next_btn.pack(side="left", padx=(2,0))
        self._update_next_btn()

        ctk.CTkButton(toolbar, text="📊 Статистика", width=110, height=28,
                      fg_color="#37474F", corner_radius=6,
                      command=self._open_stats).pack(side="right", padx=4)
        ctk.CTkButton(toolbar, text="⚙ Настройки", width=100, height=28,
                      fg_color="#37474F", corner_radius=6,
                      command=self._open_settings).pack(side="right", padx=4)
        if self._gamification_enabled:
            ctk.CTkButton(toolbar, text="🛍 Магазин", width=100, height=28,
                          fg_color="#1B5E20", corner_radius=6,
                          command=self._open_shop).pack(side="right", padx=4)

        self.task_panel = TaskPanel(
            self, self._ui_plan,
            active_task_id=self.engine.active_task_id,
            readonly=False,
            on_activate=self._activate_task,
            on_complete=self._complete_task,
            on_skip=self._ask_skip,
            on_add=self._open_add_task,
            on_copy=self._copy_task,
            on_delete=self._delete_task,
            on_edit=self._edit_task,
            on_load_templates=self._open_templates,
        )
        self.task_panel.pack(fill="both", expand=True, padx=10, pady=(4, 10))

    # ──────────────────────────────────────────────
    #  Навигация
    # ──────────────────────────────────────────────

    def _date_label(self) -> str:
        today = date.today()
        if self._current_date == today:
            return f"📅 Сегодня, {today.strftime('%d.%m')}"
        elif self._current_date == today - timedelta(days=1):
            return f"📅 Вчера, {self._current_date.strftime('%d.%m')}"
        return f"📅 {self._current_date.strftime('%d.%m.%Y')}"

    def _is_readonly(self) -> bool:
        return self._current_date != date.today()

    def _update_next_btn(self):
        if self._current_date >= date.today():
            self.next_btn.configure(state="disabled", fg_color="#2a2a2a")
        else:
            self.next_btn.configure(state="normal", fg_color="#37474F")

    def _prev_day(self):
        self._current_date -= timedelta(days=1)
        self._switch_day()

    def _next_day(self):
        if self._current_date < date.today():
            self._current_date += timedelta(days=1)
            self._switch_day()

    def _switch_day(self):
        is_today = self._current_date == date.today()
        self.date_lbl.configure(text=self._date_label())
        self._update_next_btn()

        if is_today:
            display_plan = engine_to_plan(self.engine)
            self.header.pack(fill="x", padx=10, pady=(10, 4), before=self.toolbar)
        else:
            db_plan = repo.get_plan_with_tasks(self._current_date)
            if db_plan:
                tasks = [db_task_to_ui(t) for t in db_plan.tasks]
                display_plan = DayPlan(
                    date=self._current_date.isoformat(),
                    tasks=tasks,
                    procrastination_used=db_plan.procrastination_used,
                )
            else:
                display_plan = DayPlan(date=self._current_date.isoformat())
            self.header.pack_forget()

        self.task_panel.refresh(
            display_plan,
            self.engine.active_task_id if is_today else None,
            readonly=not is_today,
        )

    # ──────────────────────────────────────────────
    #  Тик
    # ──────────────────────────────────────────────

    def _on_tick(self):
        self.after(0, self._refresh_ui)

    def _get_coin_state(self):
        """Возвращает (balance, streak) если геймификация включена, иначе (0, 0)."""
        if not getattr(self, "_gamification_enabled", False):
            return 0, 0
        try:
            bal = repo.get_balance()
            return bal.balance, bal.streak
        except Exception:
            return 0, 0

    def _refresh_ui(self):
        if self._is_readonly():
            return
        self._ui_plan = engine_to_plan(self.engine)
        coin_bal, coin_streak = self._get_coin_state()
        self.header.refresh(
            self._ui_plan, self.engine.active_task_id,
            self.engine.procrastination_remaining(),
            self.engine.procrastination_overrun(),
            coin_balance=coin_bal,
            coin_streak=coin_streak,
        )
        self.task_panel.refresh(self._ui_plan, self.engine.active_task_id)

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
        self._refresh_ui()

    def _ask_skip(self, task_id: str):
        t = self.engine.get_task(task_id)
        if not t:
            return
        tomorrow = (date.today() + timedelta(days=1)).isoformat()
        SkipDialog(
            self, t["name"],
            on_skip=lambda: self._do_skip(task_id),
            on_postpone=lambda: self._skip_and_postpone(task_id, tomorrow),
        )

    def _do_skip(self, task_id: str):
        self.engine.skip_task(task_id)
        self._refresh_ui()

    def _skip_and_postpone(self, task_id: str, to_day: str):
        t = self.engine.get_task(task_id)
        if t:
            tomorrow_plan = repo.get_or_create_plan(date.fromisoformat(to_day))
            task_id_new = str(uuid.uuid4())
            repo.add_task(tomorrow_plan.id, task_id_new,
                          t["name"], t["allocated_seconds"], t["scheduled_time"])
        self.engine.skip_task(task_id)
        self._refresh_ui()

    def _copy_task(self, task_id: str):
        t = self.engine.get_task(task_id)
        if not t:
            return
        new_id = str(uuid.uuid4())
        repo.add_task(self._today_plan_id, new_id,
                      f"{t['name']} (копия)", t["allocated_seconds"], t["scheduled_time"],
                      position=len(self.engine.get_tasks()))
        self.engine.add_task(new_id, f"{t['name']} (копия)",
                             t["allocated_seconds"], t["scheduled_time"])
        self._refresh_ui()

    def _delete_task(self, task_id: str):
        self.engine.remove_task(task_id)
        repo.delete_task(task_id)
        self._refresh_ui()

    def _edit_task(self, task_id: str):
        t = self.engine.get_task(task_id)
        if not t:
            return
        # Оборачиваем в UI Task для диалога
        ui_task = Task(
            id=t["id"], name=t["name"],
            allocated_seconds=t["allocated_seconds"],
            elapsed_seconds=t["elapsed_seconds"],
            scheduled_time=t["scheduled_time"],
            status=TaskStatus(t["status"].value),
        )
        EditTaskDialog(self, ui_task, on_save=self._save_edited_task)

    def _save_edited_task(self, ui_task: Task):
        self.engine.update_task_meta(
            ui_task.id, ui_task.name,
            ui_task.allocated_seconds, ui_task.scheduled_time,
            priority=ui_task.priority
        )
        repo.update_task(ui_task.id,
                         name=ui_task.name,
                         allocated_seconds=ui_task.allocated_seconds,
                         scheduled_time=ui_task.scheduled_time,
                         priority=ui_task.priority)
        self._refresh_ui()

    def _open_add_task(self):
        AddTaskDialog(self, on_save=self._add_task)

    def _add_task(self, ui_task: Task):
        repo.add_task(self._today_plan_id, ui_task.id,
                      ui_task.name, ui_task.allocated_seconds,
                      ui_task.scheduled_time,
                      position=len(self.engine.get_tasks()),
                      priority=ui_task.priority)
        self.engine.add_task(ui_task.id, ui_task.name,
                             ui_task.allocated_seconds, ui_task.scheduled_time,
                             priority=ui_task.priority)
        self._refresh_ui()

    def _open_templates(self):
        TemplatesDialog(self, on_load=self._load_tasks)

    def _load_tasks(self, tasks: list[Task]):
        for t in tasks:
            new_id = str(uuid.uuid4())
            repo.add_task(self._today_plan_id, new_id,
                          t.name, t.allocated_seconds, t.scheduled_time,
                          position=len(self.engine.get_tasks()))
            self.engine.add_task(new_id, t.name,
                                 t.allocated_seconds, t.scheduled_time)
        self._refresh_ui()

    # ──────────────────────────────────────────────
    #  Перенос незавершённых
    # ──────────────────────────────────────────────

    def _check_carry_over(self):
        yesterday = date.today() - timedelta(days=1)
        unfinished = repo.get_unfinished_from_date(yesterday)
        if not unfinished:
            return
        ui_tasks = [db_task_to_ui(t) for t in unfinished]
        CarryOverDialog(self, ui_tasks, on_confirm=self._carry_over_tasks)

    def _carry_over_tasks(self, tasks: list[Task]):
        for t in tasks:
            new_id = str(uuid.uuid4())
            repo.add_task(self._today_plan_id, new_id,
                          t.name, t.allocated_seconds, t.scheduled_time,
                          position=len(self.engine.get_tasks()))
            self.engine.add_task(new_id, t.name,
                                 t.allocated_seconds, t.scheduled_time)
        self._refresh_ui()

    # ──────────────────────────────────────────────
    #  Подведение итогов дня
    # ──────────────────────────────────────────────

    def _schedule_midnight_check(self):
        """Проверяем раз в минуту не наступила ли полночь."""
        now = datetime.now()
        if now.hour == 0 and now.minute == 0:
            self._finalize_yesterday()
        self.after(60_000, self._schedule_midnight_check)

    def _finalize_yesterday(self):
        yesterday = date.today() - timedelta(days=1)
        result = gami.finalize_day(yesterday)
        if result:
            self._show_day_summary(result)

    def _show_day_summary(self, result: dict):
        from tkinter import messagebox
        streak_msg = ""
        if result["streak_broken"]:
            streak_msg = "\n💔 Серия прервана!"
        elif result["streak"] > 1:
            streak_msg = f"\n🔥 Серия: {result['streak']} дней!"
        messagebox.showinfo(
            "Итог дня",
            f"Бонусы: +{result['bonus']} 🪙\n"
            f"Штрафы: -{result['penalty']} 🪙\n"
            f"Множитель: ×{result['multiplier']:.1f}\n"
            f"Итого: {result['total']:+d} 🪙"
            f"{streak_msg}"
        )

    # ──────────────────────────────────────────────
    #  Настройки / статистика
    # ──────────────────────────────────────────────

    def _open_stats(self):
        StatsPanel(self)

    def _open_shop(self):
        ShopDialog(self, on_purchase=self._on_shop_purchase)

    def _on_shop_purchase(self, new_balance: int):
        """Обновляем UI после покупки в магазине."""
        self._refresh_ui()

    def _open_settings(self):
        SettingsDialog(self, self.settings, on_save=self._apply_settings)

    def _apply_settings(self, settings: AppSettings):
        gami_changed = settings.gamification_enabled != self._gamification_enabled
        self.settings = settings
        self.engine.settings = settings
        self.notifier.settings = settings
        ctk.set_appearance_mode(settings.theme)
        if gami_changed:
            # Перестраиваем весь UI — кнопка магазина и блок коинов в хедере
            self._gamification_enabled = settings.gamification_enabled
            for w in self.winfo_children():
                w.destroy()
            self._build_ui()

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
        self.destroy()


if __name__ == "__main__":
    app = LifeTimerApp()
    app.mainloop()
