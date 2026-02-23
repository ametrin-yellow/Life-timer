import customtkinter as ctk
from typing import Optional
from models import DayPlan, Task
from ui.task_panel import fmt_time


class TimerHeader(ctk.CTkFrame):
    """
    Верхняя панель: активный таймер + счётчик прокрастинации.
    Таймер идёт всегда. Прокрастинация — пассивный счётчик, не кнопка.
    """

    def __init__(self, master, plan: DayPlan, active_task_id: Optional[str],
                 proc_remaining: int, proc_overrun: int, **kwargs):
        super().__init__(master, **kwargs)
        self.plan = plan
        self.active_task_id = active_task_id
        self.proc_remaining = proc_remaining
        self.proc_overrun = proc_overrun
        self._build()

    def _build(self):
        self.configure(corner_radius=12, fg_color="#1a1a2e")

        # Активная задача
        task_block = ctk.CTkFrame(self, fg_color="transparent")
        task_block.pack(side="left", fill="both", expand=True, padx=16, pady=12)

        ctk.CTkLabel(task_block, text="СЕЙЧАС", font=("Helvetica", 10),
                     text_color="#888").pack(anchor="w")
        self.task_name_lbl = ctk.CTkLabel(task_block, text="— прокрастинация —",
                                           font=("Helvetica", 15, "bold"), text_color="#FFB74D")
        self.task_name_lbl.pack(anchor="w")
        self.task_timer_lbl = ctk.CTkLabel(task_block, text="",
                                            font=("Helvetica", 36, "bold"), text_color="#4FC3F7")
        self.task_timer_lbl.pack(anchor="w")

        # Разделитель
        ctk.CTkFrame(self, width=2, fg_color="#333").pack(side="left", fill="y", pady=10)

        # Прокрастинация — только счётчик
        proc_block = ctk.CTkFrame(self, fg_color="transparent")
        proc_block.pack(side="left", fill="both", padx=16, pady=12)

        ctk.CTkLabel(proc_block, text="ПРОКРАСТИНАЦИЯ", font=("Helvetica", 10),
                     text_color="#888").pack(anchor="w")
        ctk.CTkLabel(proc_block, text="осталось", font=("Helvetica", 10),
                     text_color="#555").pack(anchor="w")
        self.proc_remaining_lbl = ctk.CTkLabel(proc_block, text="",
                                                font=("Helvetica", 24, "bold"), text_color="#FFB74D")
        self.proc_remaining_lbl.pack(anchor="w")
        self.proc_status_lbl = ctk.CTkLabel(proc_block, text="",
                                             font=("Helvetica", 10), text_color="#888")
        self.proc_status_lbl.pack(anchor="w")

        self._refresh_display()

    def _refresh_display(self):
        task = self._get_active_task()

        if task:
            self.task_name_lbl.configure(text=task.name, text_color="white")
            if task.is_overrun:
                over = fmt_time(task.overrun_seconds)
                self.task_timer_lbl.configure(text=f"-{over}", text_color="#EF5350")
            else:
                self.task_timer_lbl.configure(
                    text=fmt_time(task.remaining_seconds), text_color="#4FC3F7")
        else:
            self.task_name_lbl.configure(text="— прокрастинация —", text_color="#FFB74D")
            self.task_timer_lbl.configure(text="", text_color="#4FC3F7")

        # Счётчик прокрастинации
        if self.proc_overrun > 0:
            self.proc_remaining_lbl.configure(
                text=f"-{fmt_time(self.proc_overrun)}", text_color="#EF5350")
            self.proc_status_lbl.configure(text="лимит исчерпан ⚠", text_color="#EF5350")
        else:
            self.proc_remaining_lbl.configure(
                text=fmt_time(self.proc_remaining), text_color="#FFB74D")
            used = fmt_time(self.plan.procrastination_used)
            self.proc_status_lbl.configure(text=f"потрачено: {used}", text_color="#555")

    def _get_active_task(self) -> Optional[Task]:
        if not self.active_task_id:
            return None
        for t in self.plan.tasks:
            if t.id == self.active_task_id:
                return t
        return None

    def refresh(self, plan: DayPlan, active_task_id: Optional[str],
                proc_remaining: int, proc_overrun: int):
        self.plan = plan
        self.active_task_id = active_task_id
        self.proc_remaining = proc_remaining
        self.proc_overrun = proc_overrun
        self._refresh_display()
