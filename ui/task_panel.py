import customtkinter as ctk
from typing import Callable, Optional
from models import Task, TaskStatus, DayPlan


def fmt_time(seconds: int, show_sign: bool = False) -> str:
    sign = ""
    if seconds < 0:
        sign = "-"
        seconds = -seconds
    elif show_sign and seconds > 0:
        sign = "+"
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    if h > 0:
        return f"{sign}{h}:{m:02d}:{s:02d}"
    return f"{sign}{m:02d}:{s:02d}"


class TaskRow(ctk.CTkFrame):

    def __init__(self, master, task: Task, is_active: bool, readonly: bool,
                 on_activate: Callable, on_complete: Callable,
                 on_skip: Callable, on_copy: Callable, on_delete: Callable, **kwargs):
        super().__init__(master, **kwargs)
        self.task = task
        self.configure(corner_radius=8)
        self._build(is_active, readonly, on_activate, on_complete, on_skip, on_copy, on_delete)

    def _build(self, is_active, readonly, on_activate, on_complete, on_skip, on_copy, on_delete):
        left = ctk.CTkFrame(self, fg_color="transparent")
        left.pack(side="left", fill="both", expand=True, padx=8, pady=6)

        name_color = "#4CAF50" if is_active else ("white" if self.task.status == TaskStatus.PENDING else "gray")
        self.name_label = ctk.CTkLabel(left, text=self.task.name,
                                        font=("Helvetica", 13, "bold"),
                                        text_color=name_color, anchor="w")
        self.name_label.pack(anchor="w")

        if self.task.status in (TaskStatus.PENDING, TaskStatus.ACTIVE):
            progress = min(1.0, self.task.elapsed_seconds / self.task.allocated_seconds) if self.task.allocated_seconds else 0
            bar_color = "#EF5350" if self.task.is_overrun else ("#4CAF50" if is_active else "#1E88E5")
            self.progress_bar = ctk.CTkProgressBar(left, width=200, height=6,
                                                    progress_color=bar_color, fg_color="#333")
            self.progress_bar.set(progress)
            self.progress_bar.pack(anchor="w", pady=(2, 0))
        else:
            self.progress_bar = None

        self.time_label = ctk.CTkLabel(left, text=self._time_text(),
                                        font=("Helvetica", 11), anchor="w", text_color="gray")
        self.time_label.pack(anchor="w")

        right = ctk.CTkFrame(self, fg_color="transparent")
        right.pack(side="right", padx=6, pady=6)

        if readonly:
            # Только статус — никаких кнопок управления
            status_map = {
                TaskStatus.COMPLETED: ("✓ Выполнено", "#4CAF50"),
                TaskStatus.SKIPPED:   ("↷ Пропущено", "gray"),
                TaskStatus.PENDING:   ("— ожидание —", "#888"),
                TaskStatus.ACTIVE:    ("— ожидание —", "#888"),
            }
            text, color = status_map.get(self.task.status, ("", "gray"))
            ctk.CTkLabel(right, text=text, text_color=color, font=("Helvetica", 12)).pack(pady=2)
        else:
            if self.task.status in (TaskStatus.PENDING, TaskStatus.ACTIVE):
                btn_label = "⏸ Пауза" if is_active else "▶ Старт"
                btn_color = "#546E7A" if is_active else "#1E88E5"
                ctk.CTkButton(right, text=btn_label, width=90, height=26,
                              fg_color=btn_color, corner_radius=6,
                              command=lambda: on_activate(self.task.id)).pack(pady=1)
                ctk.CTkButton(right, text="✓ Готово", width=90, height=26,
                              fg_color="#388E3C", corner_radius=6,
                              command=lambda: on_complete(self.task.id)).pack(pady=1)
                ctk.CTkButton(right, text="↷ Скип", width=90, height=26,
                              fg_color="#6D4C41", corner_radius=6,
                              command=lambda: on_skip(self.task.id)).pack(pady=1)
            else:
                status_text = "✓ Выполнено" if self.task.status == TaskStatus.COMPLETED else "↷ Пропущено"
                status_color = "#4CAF50" if self.task.status == TaskStatus.COMPLETED else "gray"
                ctk.CTkLabel(right, text=status_text, text_color=status_color,
                             font=("Helvetica", 12)).pack(pady=2)

            ctk.CTkButton(right, text="⧉ Копия", width=90, height=26,
                          fg_color="#37474F", corner_radius=6,
                          command=lambda: on_copy(self.task.id)).pack(pady=1)
            ctk.CTkButton(right, text="✕ Удалить", width=90, height=26,
                          fg_color="#4a1010", corner_radius=6,
                          command=lambda: on_delete(self.task.id)).pack(pady=1)

    def _time_text(self) -> str:
        alloc = fmt_time(self.task.allocated_seconds)
        elapsed = fmt_time(self.task.elapsed_seconds)
        sched = f"  🕐 {self.task.scheduled_time}" if self.task.scheduled_time else ""
        if self.task.is_overrun:
            over = fmt_time(self.task.overrun_seconds, show_sign=True)
            return f"{elapsed} / {alloc}  ⚠ {over}{sched}"
        return f"{elapsed} / {alloc}{sched}"

    def refresh(self, task: Task, is_active: bool):
        self.task = task
        self.time_label.configure(text=self._time_text())
        name_color = "#4CAF50" if is_active else ("white" if task.status == TaskStatus.PENDING else "gray")
        self.name_label.configure(text_color=name_color)
        if self.progress_bar and task.allocated_seconds:
            progress = min(1.0, task.elapsed_seconds / task.allocated_seconds)
            bar_color = "#EF5350" if task.is_overrun else ("#4CAF50" if is_active else "#1E88E5")
            self.progress_bar.set(progress)
            self.progress_bar.configure(progress_color=bar_color)


class TaskPanel(ctk.CTkFrame):

    def __init__(self, master, plan: DayPlan, active_task_id: Optional[str],
                 readonly: bool,
                 on_activate: Callable, on_complete: Callable, on_skip: Callable,
                 on_add: Callable, on_copy: Callable, on_delete: Callable,
                 on_load_templates: Callable, **kwargs):
        super().__init__(master, **kwargs)
        self.plan = plan
        self.active_task_id = active_task_id
        self.readonly = readonly
        self.on_activate = on_activate
        self.on_complete = on_complete
        self.on_skip = on_skip
        self.on_add = on_add
        self.on_copy = on_copy
        self.on_delete = on_delete
        self.on_load_templates = on_load_templates
        self._rows: dict[str, TaskRow] = {}
        self._build()

    def _build(self):
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=10, pady=(10, 4))
        ctk.CTkLabel(header, text="📋 Задачи", font=("Helvetica", 15, "bold")).pack(side="left")

        if not self.readonly:
            btn_frame = ctk.CTkFrame(header, fg_color="transparent")
            btn_frame.pack(side="right")
            ctk.CTkButton(btn_frame, text="📋 Шаблоны", width=100, height=30,
                          fg_color="#4A148C", corner_radius=6,
                          command=self.on_load_templates).pack(side="left", padx=4)
            ctk.CTkButton(btn_frame, text="+ Добавить", width=100, height=30,
                          fg_color="#1565C0", corner_radius=6,
                          command=self.on_add).pack(side="left")

        self.scroll = ctk.CTkScrollableFrame(self, corner_radius=0, fg_color="transparent")
        self.scroll.pack(fill="both", expand=True, padx=6, pady=4)
        self._render_rows()

    def _render_rows(self):
        for w in self.scroll.winfo_children():
            w.destroy()
        self._rows.clear()

        if not self.plan.tasks:
            ctk.CTkLabel(self.scroll, text="Нет задач на этот день",
                         text_color="gray", font=("Helvetica", 13)).pack(pady=20)
            return

        for task in self.plan.tasks:
            is_active = task.id == self.active_task_id
            row = TaskRow(
                self.scroll, task, is_active, self.readonly,
                on_activate=self._handle_activate,
                on_complete=self.on_complete,
                on_skip=self.on_skip,
                on_copy=self.on_copy,
                on_delete=self.on_delete,
                fg_color=("#2b2b2b" if task.status == TaskStatus.PENDING else "#1e1e1e")
            )
            row.pack(fill="x", pady=3)
            self._rows[task.id] = row

    def _handle_activate(self, task_id: str):
        if self.active_task_id == task_id:
            self.on_activate(None)
        else:
            self.on_activate(task_id)

    def refresh(self, plan: DayPlan, active_task_id: Optional[str], readonly: bool = False):
        self.plan = plan
        self.active_task_id = active_task_id
        self.readonly = readonly
        task_ids = [t.id for t in plan.tasks]
        existing_ids = list(self._rows.keys())
        if task_ids != existing_ids:
            self._render_rows()
            return
        for task in plan.tasks:
            if task.id in self._rows:
                self._rows[task.id].refresh(task, task.id == active_task_id)
