import customtkinter as ctk
from typing import Callable
from models import Task


class CarryOverDialog(ctk.CTkToplevel):
    """Предложение перенести незавершённые задачи с прошлого дня."""

    def __init__(self, master, tasks: list[Task],
                 on_confirm: Callable[[list[Task]], None], **kwargs):
        super().__init__(master, **kwargs)
        self.title("Незавершённые задачи")
        self.geometry("420x360")
        self.resizable(False, False)
        self.tasks = tasks
        self.on_confirm = on_confirm
        self.vars: list[ctk.BooleanVar] = []
        self.after(100, self._force_focus)
        self.after(150, self.grab_set)
        self._build()

    def _force_focus(self):
        self.attributes("-topmost", True)
        self.lift()
        self.focus_force()
        self.after(200, lambda: self.attributes("-topmost", False))

    def _build(self):
        ctk.CTkLabel(self, text="Вчера остались незавершённые задачи",
                     font=("Helvetica", 14, "bold")).pack(pady=(16, 4))
        ctk.CTkLabel(self, text="Выбери что перенести на сегодня:",
                     text_color="gray", font=("Helvetica", 12)).pack()

        frame = ctk.CTkScrollableFrame(self, height=180, corner_radius=8)
        frame.pack(fill="x", padx=16, pady=10)

        for task in self.tasks:
            var = ctk.BooleanVar(value=True)
            self.vars.append(var)
            row = ctk.CTkFrame(frame, fg_color="transparent")
            row.pack(fill="x", pady=2)
            ctk.CTkCheckBox(row, text=task.name, variable=var,
                            font=("Helvetica", 12)).pack(side="left", padx=8)
            mins = task.allocated_seconds // 60
            ctk.CTkLabel(row, text=f"{mins} мин", text_color="gray",
                         font=("Helvetica", 11)).pack(side="right", padx=8)

        btns = ctk.CTkFrame(self, fg_color="transparent")
        btns.pack(pady=10)
        ctk.CTkButton(btns, text="Перенести выбранные", width=160, height=34,
                      fg_color="#1B5E20", corner_radius=6,
                      command=self._confirm).pack(side="left", padx=6)
        ctk.CTkButton(btns, text="Пропустить", width=100, height=34,
                      fg_color="#444", corner_radius=6,
                      command=self.destroy).pack(side="left", padx=6)

    def _confirm(self):
        selected = [t for t, v in zip(self.tasks, self.vars) if v.get()]
        if selected:
            self.on_confirm(selected)
        self.destroy()
