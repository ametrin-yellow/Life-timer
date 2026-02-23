import customtkinter as ctk
from tkinter import messagebox
from typing import Callable
from models import AppSettings, OverrunBehavior, OverrunSource
import storage


class SettingsDialog(ctk.CTkToplevel):

    BEHAVIOR_OPTIONS = {
        "Продолжать (уходить в минус)": OverrunBehavior.CONTINUE,
        "Остановить таймер задачи":     OverrunBehavior.STOP,
    }
    SOURCE_OPTIONS = {
        "Отъедать от прокрастинации":        OverrunSource.PROCRASTINATION,
        "Пропорционально от остальных задач": OverrunSource.PROPORTIONAL,
    }

    def __init__(self, master, settings: AppSettings, on_save: Callable[[AppSettings], None], **kwargs):
        super().__init__(master, **kwargs)
        self.title("⚙ Настройки")
        self.geometry("440x500")
        self.resizable(False, False)
        self.settings = settings
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

        ctk.CTkLabel(self, text="Настройки", font=("Helvetica", 16, "bold")).pack(pady=(16, 8))

        # Поведение при перерасходе
        ctk.CTkLabel(self, text="Когда время задачи вышло:", anchor="w",
                     font=("Helvetica", 12, "bold")).pack(fill="x", **pad)
        behavior_opts = list(self.BEHAVIOR_OPTIONS.keys())
        current_behavior = next(k for k, v in self.BEHAVIOR_OPTIONS.items()
                                if v == self.settings.overrun_behavior)
        self.behavior_var = ctk.StringVar(value=current_behavior)
        self.behavior_menu = ctk.CTkOptionMenu(self, values=behavior_opts,
                                                variable=self.behavior_var,
                                                command=self._on_behavior_change)
        self.behavior_menu.pack(fill="x", **pad)

        # Источник времени (только если CONTINUE)
        self.source_label = ctk.CTkLabel(self, text="Откуда брать время при перерасходе:",
                                          anchor="w", font=("Helvetica", 12, "bold"))
        self.source_label.pack(fill="x", **pad)
        source_opts = list(self.SOURCE_OPTIONS.keys())
        current_source = next(k for k, v in self.SOURCE_OPTIONS.items()
                              if v == self.settings.overrun_source)
        self.source_var = ctk.StringVar(value=current_source)
        self.source_menu = ctk.CTkOptionMenu(self, values=source_opts, variable=self.source_var)
        self.source_menu.pack(fill="x", **pad)

        # Обновим состояние source сразу
        self._on_behavior_change(current_behavior)

        ctk.CTkFrame(self, height=1, fg_color="#333").pack(fill="x", padx=20, pady=8)

        ctk.CTkLabel(self, text="Лимит прокрастинации (мин, пусто = авто 24ч − задачи):",
                     anchor="w", wraplength=400).pack(fill="x", **pad)
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

    def _on_behavior_change(self, value: str):
        is_continue = self.BEHAVIOR_OPTIONS[value] == OverrunBehavior.CONTINUE
        state = "normal" if is_continue else "disabled"
        self.source_menu.configure(state=state)
        self.source_label.configure(text_color="white" if is_continue else "gray")

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

        self.settings.overrun_behavior = self.BEHAVIOR_OPTIONS[self.behavior_var.get()]
        self.settings.overrun_source = self.SOURCE_OPTIONS[self.source_var.get()]
        self.settings.procrastination_override_minutes = proc_override
        self.settings.notify_before_minutes = notify_min
        storage.save_settings(self.settings)
        self.on_save(self.settings)
        self.destroy()
