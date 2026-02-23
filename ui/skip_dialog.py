import customtkinter as ctk
from typing import Callable


class SkipDialog(ctk.CTkToplevel):
    """Диалог при скипе — просто скип или перенести на завтра."""

    def __init__(self, master, task_name: str,
                 on_skip: Callable, on_postpone: Callable, **kwargs):
        super().__init__(master, **kwargs)
        self.title("Пропустить задачу")
        self.geometry("380x180")
        self.resizable(False, False)
        self._on_skip = on_skip
        self._on_postpone = on_postpone
        self._build(task_name)
        self.after(100, self._force_focus)
        self.after(150, self.grab_set)

    def _force_focus(self):
        self.attributes("-topmost", True)
        self.lift()
        self.focus_force()
        self.after(200, lambda: self.attributes("-topmost", False))

    def _build(self, task_name: str):
        ctk.CTkLabel(self, text=f"«{task_name}»",
                     font=("Helvetica", 14, "bold"), wraplength=340).pack(pady=(18, 4))
        ctk.CTkLabel(self, text="Что сделать с задачей?",
                     text_color="gray", font=("Helvetica", 12)).pack()

        btns = ctk.CTkFrame(self, fg_color="transparent")
        btns.pack(pady=14)

        ctk.CTkButton(btns, text="↷ Просто скип", width=120, height=34,
                      fg_color="#6D4C41", corner_radius=6,
                      command=lambda: self._choose(self._on_skip)).pack(side="left", padx=5)
        ctk.CTkButton(btns, text="📅 На завтра", width=120, height=34,
                      fg_color="#1565C0", corner_radius=6,
                      command=lambda: self._choose(self._on_postpone)).pack(side="left", padx=5)
        ctk.CTkButton(btns, text="Отмена", width=80, height=34,
                      fg_color="#444", corner_radius=6,
                      command=self.destroy).pack(side="left", padx=5)

    def _choose(self, cb: Callable):
        self.destroy()
        cb()
