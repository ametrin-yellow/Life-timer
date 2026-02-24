import customtkinter as ctk
from typing import Callable, Optional
from adapter import Task, TaskStatus, DayPlan, Priority
import validation

# Конфигурация приоритетов
PRIORITY_CFG = {
    Priority.HIGH:   {"label": "🔴 Высокий", "color": "#EF5350", "sort_key": 0},
    Priority.NORMAL: {"label": "🟡 Средний",  "color": "#FFB74D", "sort_key": 1},
    Priority.LOW:    {"label": "🔵 Низкий",   "color": "#90A4AE", "sort_key": 2},
}


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


def sort_tasks(tasks, active_task_id=None):
    """
    Сортировка задач:
    Активные/ожидающие:
      1. Приоритет (High → Normal → Low)
      2. Запускалась (elapsed > 0)
      3. Есть scheduled_time
      4. Длительность (больше — выше)
      5. Алфавит
    Завершённые/скипнутые — внизу, в порядке завершения (completed_at)
    """
    from adapter import TaskStatus
    active = [t for t in tasks if t.status in (TaskStatus.PENDING, TaskStatus.ACTIVE)]
    done = [t for t in tasks if t.status in (TaskStatus.COMPLETED, TaskStatus.SKIPPED)]

    def active_key(t):
        pri = PRIORITY_CFG.get(t.priority, PRIORITY_CFG[Priority.NORMAL])["sort_key"]
        return (
            pri,                                       # приоритет — главный
            0 if t.elapsed_seconds > 0 else 1,        # запускалась — выше
            0 if t.scheduled_time else 1,              # есть время — выше
            -t.allocated_seconds,                      # длиннее — выше
            t.name.lower(),                            # алфавит
        )

    # Активная (тикающая прямо сейчас) — всегда первая

    active.sort(key=active_key)
    if active_task_id:
        active.sort(key=lambda t: 0 if t.id == active_task_id else 1)
    done.sort(key=lambda t: t.completed_at or "")
    return active + done



class TaskRow(ctk.CTkFrame):

    def __init__(self, master, task: Task, is_active: bool, readonly: bool,
                 on_activate: Callable, on_complete: Callable,
                 on_skip: Callable, on_copy: Callable, on_delete: Callable,
                 on_edit: Callable, **kwargs):
        super().__init__(master, **kwargs)
        self.task = task
        self.is_active = is_active
        self.readonly = readonly
        self._on_activate = on_activate
        self._on_complete = on_complete
        self._on_skip = on_skip
        self._on_copy = on_copy
        self._on_delete = on_delete
        self._on_edit = on_edit
        self._menu_open = False
        self._menu_frame: Optional[ctk.CTkFrame] = None
        self.configure(corner_radius=8)
        self._build()

    def _build(self):
        # Левая часть — название + прогресс + время
        left = ctk.CTkFrame(self, fg_color="transparent")
        left.pack(side="left", fill="both", expand=True, padx=8, pady=6)

        name_color = "#4CAF50" if self.is_active else (
            "white" if self.task.status == TaskStatus.PENDING else "gray")

        # Строка с именем + бейдж приоритета
        name_row = ctk.CTkFrame(left, fg_color="transparent")
        name_row.pack(anchor="w", fill="x")

        self.name_label = ctk.CTkLabel(name_row, text=self.task.name,
                                        font=("Helvetica", 13, "bold"),
                                        text_color=name_color, anchor="w")
        self.name_label.pack(side="left")

        # Бейдж приоритета — всегда показываем
        pri_cfg = PRIORITY_CFG.get(self.task.priority, PRIORITY_CFG[Priority.NORMAL])
        from ui.tooltip import Tooltip, TIPS
        tip_key = ("priority_high" if self.task.priority == Priority.HIGH
                   else "priority_low" if self.task.priority == Priority.LOW
                   else "priority_normal")
        self.priority_badge = ctk.CTkLabel(name_row, text=pri_cfg["label"],
                         font=("Helvetica", 10), text_color=pri_cfg["color"],
                         fg_color="#2a2a2a", corner_radius=4,
                         padx=4, pady=1)
        self.priority_badge.pack(side="left", padx=(6, 0))
        Tooltip(self.priority_badge, TIPS[tip_key])

        if self.task.status in (TaskStatus.PENDING, TaskStatus.ACTIVE):
            progress = min(1.0, self.task.elapsed_seconds / self.task.allocated_seconds) \
                if self.task.allocated_seconds else 0
            bar_color = "#EF5350" if self.task.is_overrun else (
                "#4CAF50" if self.is_active else "#1E88E5")
            self.progress_bar = ctk.CTkProgressBar(left, width=200, height=6,
                                                    progress_color=bar_color, fg_color="#333")
            self.progress_bar.set(progress)
            self.progress_bar.pack(anchor="w", pady=(2, 0))
        else:
            self.progress_bar = None

        # Строка времени + монеты
        time_coins_row = ctk.CTkFrame(left, fg_color="transparent")
        time_coins_row.pack(anchor="w", fill="x")

        self.time_label = ctk.CTkLabel(time_coins_row, text=self._time_text(),
                                        font=("Helvetica", 11), anchor="w", text_color="gray")
        self.time_label.pack(side="left")

        # Превью монет — отдельный виджет, заметный
        if self.task.status in (TaskStatus.PENDING, TaskStatus.ACTIVE):
            coins_text, coins_color = self._coins_preview()
            self.coins_label = ctk.CTkLabel(
                time_coins_row, text=coins_text,
                font=("Helvetica", 12, "bold"),
                text_color=coins_color,
                fg_color="#1a2a1a" if coins_color != "#555" else "#1a1a1a",
                corner_radius=4, padx=5, pady=1
            )
            self.coins_label.pack(side="left", padx=(8, 0))
            from ui.tooltip import Tooltip, TIPS
            Tooltip(self.coins_label, TIPS["coins_task_preview"])
        else:
            self.coins_label = None

        # Правая часть
        right = ctk.CTkFrame(self, fg_color="transparent")
        right.pack(side="right", padx=6, pady=6)

        if self.readonly:
            status_map = {
                TaskStatus.COMPLETED: ("✓ Выполнено", "#4CAF50"),
                TaskStatus.SKIPPED:   ("↷ Пропущено", "gray"),
                TaskStatus.PENDING:   ("— ожидание —", "#888"),
                TaskStatus.ACTIVE:    ("— ожидание —", "#888"),
            }
            text, color = status_map.get(self.task.status, ("", "gray"))
            ctk.CTkLabel(right, text=text, text_color=color, font=("Helvetica", 12)).pack(pady=2)
            return

        # Кнопки действий — горизонтально
        actions = ctk.CTkFrame(right, fg_color="transparent")
        actions.pack()

        if self.task.status in (TaskStatus.PENDING, TaskStatus.ACTIVE):
            btn_label = "⏸" if self.is_active else "▶"
            btn_color = "#546E7A" if self.is_active else "#1E88E5"
            ctk.CTkButton(actions, text=btn_label, width=36, height=30,
                          fg_color=btn_color, corner_radius=6,
                          command=lambda: self._on_activate(self.task.id)).pack(side="left", padx=2)
            ctk.CTkButton(actions, text="✓", width=36, height=30,
                          fg_color="#388E3C", corner_radius=6,
                          command=lambda: self._on_complete(self.task.id)).pack(side="left", padx=2)
            ctk.CTkButton(actions, text="↷", width=36, height=30,
                          fg_color="#6D4C41", corner_radius=6,
                          command=lambda: self._on_skip(self.task.id)).pack(side="left", padx=2)
        else:
            status_text = "✓ Выполнено" if self.task.status == TaskStatus.COMPLETED else "↷ Пропущено"
            status_color = "#4CAF50" if self.task.status == TaskStatus.COMPLETED else "gray"
            ctk.CTkLabel(actions, text=status_text, text_color=status_color,
                         font=("Helvetica", 12)).pack(side="left", padx=4)

        # Кнопка меню ⋯ — для незавершённых задач (PENDING или ACTIVE статус)
        if not self.is_active and self.task.status in (TaskStatus.PENDING, TaskStatus.ACTIVE):
            self.menu_btn = ctk.CTkButton(actions, text="⋯", width=36, height=30,
                                           fg_color="#37474F", corner_radius=6,
                                           command=self._toggle_menu)
            self.menu_btn.pack(side="left", padx=2)

    def _toggle_menu(self):
        if self._menu_open:
            self._close_menu()
        else:
            self._open_menu()

    def _open_menu(self):
        self._menu_open = True
        self._menu_frame = ctk.CTkFrame(self, fg_color="#263238", corner_radius=6,
                                         border_width=1, border_color="#444")
        self._menu_frame.pack(fill="x", padx=8, pady=(0, 6))

        btns = ctk.CTkFrame(self._menu_frame, fg_color="transparent")
        btns.pack(padx=6, pady=6)

        # Редактировать — только если не активна
        if not self.is_active:
            ctk.CTkButton(btns, text="✎ Изменить", width=100, height=26,
                          fg_color="#4A148C", corner_radius=5,
                          command=lambda: [self._close_menu(), self._on_edit(self.task.id)]
                          ).pack(side="left", padx=3)

        ctk.CTkButton(btns, text="⧉ Копия", width=90, height=26,
                      fg_color="#37474F", corner_radius=5,
                      command=lambda: [self._close_menu(), self._on_copy(self.task.id)]
                      ).pack(side="left", padx=3)

        ctk.CTkButton(btns, text="✕ Удалить", width=90, height=26,
                      fg_color="#4a1010", corner_radius=5,
                      command=lambda: [self._close_menu(), self._on_delete(self.task.id)]
                      ).pack(side="left", padx=3)

    def _close_menu(self):
        self._menu_open = False
        if self._menu_frame:
            self._menu_frame.destroy()
            self._menu_frame = None

    def _coins_preview(self) -> tuple[str, str]:
        """Возвращает (текст, цвет) для превью монет."""
        try:
            from gamification import calc_task_base_coins
            coins = calc_task_base_coins(self.task)
            if coins > 0:
                return f"🪙 ~{coins}", "#4CAF50"
            else:
                return "🪙 0", "#555"
        except Exception:
            return "", "#555"

    def _time_text(self) -> str:
        alloc = fmt_time(self.task.allocated_seconds)
        elapsed = fmt_time(self.task.elapsed_seconds)
        sched = f"  🕐 {self.task.scheduled_time}" if self.task.scheduled_time else ""
        if self.task.is_overrun:
            over = fmt_time(self.task.overrun_seconds, show_sign=True)
            return f"{elapsed} / {alloc}  ⚠ {over}{sched}"
        return f"{elapsed} / {alloc}{sched}"

    def refresh(self, task: Task, is_active: bool):
        priority_changed = task.priority != self.task.priority
        active_changed = is_active != self.is_active
        self.task = task
        self.is_active = is_active
        if active_changed or priority_changed:
            for w in self.winfo_children():
                w.destroy()
            self._menu_open = False
            self._menu_frame = None
            self._build()
            return
        self.time_label.configure(text=self._time_text())
        name_color = "#4CAF50" if is_active else (
            "white" if task.status == TaskStatus.PENDING else "gray")
        self.name_label.configure(text_color=name_color)
        # Обновляем бейдж приоритета (всегда существует)
        if self.priority_badge:
            pri_cfg = PRIORITY_CFG.get(task.priority, PRIORITY_CFG[Priority.NORMAL])
            self.priority_badge.configure(text=pri_cfg["label"], text_color=pri_cfg["color"])
        if self.progress_bar and task.allocated_seconds:
            progress = min(1.0, task.elapsed_seconds / task.allocated_seconds)
            bar_color = "#EF5350" if task.is_overrun else (
                "#4CAF50" if is_active else "#1E88E5")
            self.progress_bar.set(progress)
            self.progress_bar.configure(progress_color=bar_color)
        if self.coins_label:
            coins_text, coins_color = self._coins_preview()
            bg = "#1a2a1a" if coins_color != "#555" else "#1a1a1a"
            self.coins_label.configure(text=coins_text, text_color=coins_color, fg_color=bg)


class TaskPanel(ctk.CTkFrame):

    def __init__(self, master, plan: DayPlan, active_task_id: Optional[str],
                 readonly: bool,
                 on_activate: Callable, on_complete: Callable, on_skip: Callable,
                 on_add: Callable, on_copy: Callable, on_delete: Callable,
                 on_edit: Callable, on_load_templates: Callable, **kwargs):
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
        self.on_edit = on_edit
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

        self.warnings_bar = ctk.CTkFrame(self, fg_color="transparent")
        # warnings_bar показывается только когда есть предупреждения (_update_warnings)
        self._update_warnings()

    def _render_rows(self):
        for w in self.scroll.winfo_children():
            w.destroy()
        self._rows.clear()

        if not self.plan.tasks:
            ctk.CTkLabel(self.scroll, text="Нет задач на этот день",
                         text_color="gray", font=("Helvetica", 13)).pack(pady=20)
            return

        for task in sort_tasks(self.plan.tasks, self.active_task_id):
            is_active = task.id == self.active_task_id
            row = TaskRow(
                self.scroll, task, is_active, self.readonly,
                on_activate=self._handle_activate,
                on_complete=self.on_complete,
                on_skip=self.on_skip,
                on_copy=self.on_copy,
                on_delete=self.on_delete,
                on_edit=self.on_edit,
                fg_color=("#2b2b2b" if task.status == TaskStatus.PENDING else "#1e1e1e")
            )
            row.pack(fill="x", pady=3)
            self._rows[task.id] = row

    def _handle_activate(self, task_id: str):
        if self.active_task_id == task_id:
            self.on_activate(None)
        else:
            self.on_activate(task_id)

    def _update_warnings(self):
        for w in self.warnings_bar.winfo_children():
            w.destroy()
        if self.readonly:
            self.warnings_bar.pack_forget()
            return
        warns = validation.check_plan(self.plan)
        if warns:
            self.warnings_bar.pack(fill="x", padx=6, pady=(0, 4))
            for msg in warns:
                ctk.CTkLabel(self.warnings_bar, text=msg,
                             fg_color="#4a3000", corner_radius=6,
                             text_color="#FFB74D", font=("Helvetica", 11),
                             anchor="w").pack(fill="x", padx=4, pady=1)
        else:
            self.warnings_bar.pack_forget()

    def refresh(self, plan: DayPlan, active_task_id: Optional[str], readonly: bool = False):
        readonly_changed = readonly != self.readonly
        self.plan = plan
        self.active_task_id = active_task_id
        self.readonly = readonly
        if readonly_changed:
            for w in self.winfo_children():
                w.destroy()
            self._rows.clear()
            self._build()
            return
        task_ids = [t.id for t in sort_tasks(plan.tasks, active_task_id)]
        existing_ids = list(self._rows.keys())
        if task_ids != existing_ids:
            self._render_rows()
            return
        for task in sort_tasks(plan.tasks):
            if task.id in self._rows:
                self._rows[task.id].refresh(task, task.id == active_task_id)
        self._update_warnings()
