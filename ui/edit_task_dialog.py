import customtkinter as ctk
from tkinter import messagebox
import re
from typing import Callable
from adapter import Task, Priority


class EditTaskDialog(ctk.CTkToplevel):
    """Редактирование существующей задачи."""

    def __init__(self, master, task: Task, on_save: Callable[[Task], None], **kwargs):
        super().__init__(master, **kwargs)
        self.title("Редактировать задачу")
        self.geometry("380x360")
        self.resizable(False, False)
        self.task = task
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

        ctk.CTkLabel(self, text="Название:", anchor="w").pack(fill="x", **pad)
        self.name_entry = ctk.CTkEntry(self)
        self.name_entry.insert(0, self.task.name)
        self.name_entry.pack(fill="x", **pad)

        ctk.CTkLabel(self, text="Оставшееся время (минуты):", anchor="w").pack(fill="x", **pad)
        self.minutes_entry = ctk.CTkEntry(self)
        remaining_min = self.task.remaining_seconds / 60
        self.minutes_entry.insert(0, f"{remaining_min:.0f}")
        self.minutes_entry.pack(fill="x", **pad)

        ctk.CTkLabel(self, text="Начало (ЧЧ:ММ, опционально):", anchor="w").pack(fill="x", **pad)
        self.time_entry = ctk.CTkEntry(self, placeholder_text="14:30")
        if self.task.scheduled_time:
            self.time_entry.insert(0, self.task.scheduled_time)
        self.time_entry.pack(fill="x", **pad)

        # Приоритет
        ctk.CTkLabel(self, text="Приоритет:", anchor="w").pack(fill="x", **pad)
        current_priority = self.task.priority if self.task.priority else Priority.NORMAL
        self._priority_var = ctk.StringVar(value=current_priority.value)
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
        btns.pack(pady=14)
        ctk.CTkButton(btns, text="Отмена", width=100, fg_color="#444",
                      command=self.destroy).pack(side="left", padx=6)
        ctk.CTkButton(btns, text="Сохранить", width=120, fg_color="#1565C0",
                      command=self._save).pack(side="left", padx=6)

        self.name_entry.focus()

    def _save(self):
        name = self.name_entry.get().strip()
        if not name:
            messagebox.showerror("Ошибка", "Введи название", parent=self)
            return

        try:
            minutes = float(self.minutes_entry.get().strip())
            if minutes <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Ошибка", "Введи корректное время (минуты > 0)", parent=self)
            return

        scheduled = self.time_entry.get().strip() or None
        if scheduled and not re.match(r"^\d{1,2}:\d{2}$", scheduled):
            messagebox.showerror("Ошибка", "Время в формате ЧЧ:ММ", parent=self)
            return

        self.task.name = name
        self.task.allocated_seconds = self.task.elapsed_seconds + int(minutes * 60)
        self.task.scheduled_time = scheduled
        self.task.priority = Priority(self._priority_var.get())
        self.on_save(self.task)
        self.destroy()

