import customtkinter as ctk
from tkinter import messagebox
from typing import Callable, Optional
from adapter import Task, Priority


class AddTaskDialog(ctk.CTkToplevel):
    """Диалог добавления задачи."""

    def __init__(self, master, on_save: Callable[[Task], None], **kwargs):
        super().__init__(master, **kwargs)
        self.title("Новая задача")
        self.geometry("380x370")
        self.resizable(False, False)
        self.on_save = on_save
        self.after(100, self._force_focus)
        self.after(150, self.grab_set)
        self._build()

    def _force_focus(self):
        self.attributes("-topmost", True)
        self.lift()
        self.focus_force()
        self.after(200, lambda: self.attributes("-topmost", False))

    def _build(self):
        pad = {"padx": 20, "pady": 6}

        ctk.CTkLabel(self, text="Название задачи:", anchor="w").pack(fill="x", **pad)
        self.name_entry = ctk.CTkEntry(self, placeholder_text="например: Написать отчёт")
        self.name_entry.pack(fill="x", **pad)

        ctk.CTkLabel(self, text="Время (минуты):", anchor="w").pack(fill="x", **pad)
        self.minutes_entry = ctk.CTkEntry(self, placeholder_text="30")
        self.minutes_entry.pack(fill="x", **pad)

        ctk.CTkLabel(self, text="Начало (ЧЧ:ММ, опционально):", anchor="w").pack(fill="x", **pad)
        self.time_entry = ctk.CTkEntry(self, placeholder_text="14:30")
        self.time_entry.pack(fill="x", **pad)

        # Приоритет
        ctk.CTkLabel(self, text="Приоритет:", anchor="w").pack(fill="x", **pad)
        self._priority_var = ctk.StringVar(value=Priority.NORMAL.value)
        priority_frame = ctk.CTkFrame(self, fg_color="transparent")
        priority_frame.pack(fill="x", padx=20, pady=2)
        for pri, cfg in [
            (Priority.HIGH,   ("🔴 Высокий", "#EF5350")),
            (Priority.NORMAL, ("🟡 Средний",  "#FFB74D")),
            (Priority.LOW,    ("🔵 Низкий",   "#90A4AE")),
        ]:
            ctk.CTkRadioButton(
                priority_frame, text=cfg[0],
                variable=self._priority_var, value=pri.value,
                text_color=cfg[1]
            ).pack(side="left", padx=8)

        btns = ctk.CTkFrame(self, fg_color="transparent")
        btns.pack(pady=12)
        ctk.CTkButton(btns, text="Отмена", width=100, fg_color="#444",
                      command=self.destroy).pack(side="left", padx=6)
        ctk.CTkButton(btns, text="Добавить", width=120, fg_color="#1565C0",
                      command=self._save).pack(side="left", padx=6)

        self.name_entry.focus()

    def _save(self):
        name = self.name_entry.get().strip()
        if not name:
            messagebox.showerror("Ошибка", "Введи название задачи", parent=self)
            return

        try:
            minutes = float(self.minutes_entry.get().strip() or "25")
            if minutes <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Ошибка", "Введи корректное время (минуты > 0)", parent=self)
            return

        scheduled = self.time_entry.get().strip() or None
        if scheduled:
            import re
            if not re.match(r"^\d{1,2}:\d{2}$", scheduled):
                messagebox.showerror("Ошибка", "Время должно быть в формате ЧЧ:ММ", parent=self)
                return

        priority = Priority(self._priority_var.get())

        task = Task(
            name=name,
            allocated_seconds=int(minutes * 60),
            scheduled_time=scheduled,
            priority=priority,
        )
        self.on_save(task)
        self.destroy()

