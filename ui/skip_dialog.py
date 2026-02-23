import customtkinter as ctk
from typing import Callable


class SkipDialog(ctk.CTkToplevel):
    """Диалог при скипе — просто скип или перенести на завтра."""

    def __init__(self, master, task_name: str,
                 on_skip: Callable, on_postpone: Callable, **kwargs):
        super().__init__(master, **kwargs)
        self.title("Пропустить задачу")
        self.geometry("360x200")
        self.resizable(False, False)
        self.after(100, self.lift)
        self.after(100, self.grab_set)

        ctk.CTkLabel(self, text=f"«{task_name}»",
                     font=("Helvetica", 14, "bold"), wraplength=320).pack(pady=(20, 6))
        ctk.CTkLabel(self, text="Что сделать с задачей?",
                     text_color="gray", font=("Helvetica", 12)).pack()

        btns = ctk.CTkFrame(self, fg_color="transparent")
        btns.pack(pady=16)

        ctk.CTkButton(btns, text="↷ Просто скип", width=120, height=34,
                      fg_color="#6D4C41", corner_radius=6,
                      command=lambda: self._choose(on_skip)).pack(side="left", padx=6)
        ctk.CTkButton(btns, text="📅 На завтра", width=120, height=34,
                      fg_color="#1565C0", corner_radius=6,
                      command=lambda: self._choose(on_postpone)).pack(side="left", padx=6)
        ctk.CTkButton(btns, text="Отмена", width=80, height=34,
                      fg_color="#444", corner_radius=6,
                      command=self.destroy).pack(side="left", padx=6)

    def _choose(self, cb: Callable):
        self.destroy()
        cb()
