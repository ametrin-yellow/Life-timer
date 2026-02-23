import customtkinter as ctk
from tkinter import messagebox
from typing import Callable
from models import AppSettings, OverrunMode
import storage


class SettingsDialog(ctk.CTkToplevel):

    OVERRUN_OPTIONS = {
        "Уходить в минус": OverrunMode.MINUS,
        "Отъедать от прокрастинации": OverrunMode.EAT_PROCRASTINATION,
        "Пропорционально от задач": OverrunMode.EAT_PROPORTIONAL,
    }

    def __init__(self, master, settings: AppSettings, on_save: Callable[[AppSettings], None], **kwargs):
        super().__init__(master, **kwargs)
        self.title("⚙ Настройки")
        self.geometry("420x440")
        self.resizable(False, False)
        self.settings = settings
        self.on_save = on_save
        self.after(100, self.lift)
        self.after(100, self.grab_set)
        self._build()

    def _build(self):
        pad = {"padx": 20, "pady": 8}

        ctk.CTkLabel(self, text="Настройки", font=("Helvetica", 16, "bold")).pack(pady=(16, 4))

        ctk.CTkLabel(self, text="Поведение при перерасходе задачи:", anchor="w").pack(fill="x", **pad)
        options = list(self.OVERRUN_OPTIONS.keys())
        current = next(k for k, v in self.OVERRUN_OPTIONS.items() if v == self.settings.overrun_mode)
        self.overrun_var = ctk.StringVar(value=current)
        ctk.CTkOptionMenu(self, values=options, variable=self.overrun_var).pack(fill="x", **pad)

        ctk.CTkLabel(self, text="Лимит прокрастинации (мин, пусто = авто 24ч − задачи):",
                     anchor="w", wraplength=380).pack(fill="x", **pad)
        self.proc_entry = ctk.CTkEntry(self, placeholder_text="авто")
        if self.settings.procrastination_override_minutes is not None:
            self.proc_entry.insert(0, str(self.settings.procrastination_override_minutes))
        self.proc_entry.pack(fill="x", **pad)

        ctk.CTkLabel(self, text="Уведомлять за N минут до задачи:", anchor="w").pack(fill="x", **pad)
        self.notify_entry = ctk.CTkEntry(self)
        self.notify_entry.insert(0, str(self.settings.notify_before_minutes))
        self.notify_entry.pack(fill="x", **pad)

        btns = ctk.CTkFrame(self, fg_color="transparent")
        btns.pack(pady=16)
        ctk.CTkButton(btns, text="Отмена", width=100, fg_color="#444",
                      command=self.destroy).pack(side="left", padx=6)
        ctk.CTkButton(btns, text="Сохранить", width=120, fg_color="#1B5E20",
                      command=self._save).pack(side="left", padx=6)

    def _save(self):
        proc_val = self.proc_entry.get().strip()
        proc_override = None
        if proc_val:
            try:
                proc_override = int(proc_val)
                if proc_override <= 0:
                    raise ValueError
            except ValueError:
                messagebox.showerror("Ошибка", "Лимит прокрастинации — целое число > 0 или пусто", parent=self)
                return

        try:
            notify_min = int(self.notify_entry.get().strip())
            if notify_min < 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Ошибка", "Введи корректное число минут", parent=self)
            return

        self.settings.overrun_mode = self.OVERRUN_OPTIONS[self.overrun_var.get()]
        self.settings.procrastination_override_minutes = proc_override
        self.settings.notify_before_minutes = notify_min
        storage.save_settings(self.settings)
        self.on_save(self.settings)
        self.destroy()
