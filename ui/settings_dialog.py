import customtkinter as ctk
from tkinter import messagebox
from typing import Callable
from adapter import AppSettings, OverrunBehavior, OverrunSource
import repository as storage


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
        self.geometry("460x620")
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
        pad = {"padx": 20, "pady": 5}

        ctk.CTkLabel(self, text="Настройки", font=("Helvetica", 16, "bold")).pack(pady=(16, 8))

        # ── Поведение при перерасходе ──
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

        self.source_label = ctk.CTkLabel(self, text="Откуда брать время при перерасходе:",
                                          anchor="w", font=("Helvetica", 12, "bold"))
        self.source_label.pack(fill="x", **pad)
        source_opts = list(self.SOURCE_OPTIONS.keys())
        current_source = next(k for k, v in self.SOURCE_OPTIONS.items()
                              if v == self.settings.overrun_source)
        self.source_var = ctk.StringVar(value=current_source)
        self.source_menu = ctk.CTkOptionMenu(self, values=source_opts, variable=self.source_var)
        self.source_menu.pack(fill="x", **pad)
        self._on_behavior_change(current_behavior)

        ctk.CTkFrame(self, height=1, fg_color="#333").pack(fill="x", padx=20, pady=8)

        # ── Уведомления ──
        ctk.CTkLabel(self, text="Уведомлять за N минут до задачи:", anchor="w").pack(fill="x", **pad)
        self.notify_entry = ctk.CTkEntry(self)
        self.notify_entry.insert(0, str(self.settings.notify_before_minutes))
        self.notify_entry.pack(fill="x", **pad)

        ctk.CTkFrame(self, height=1, fg_color="#333").pack(fill="x", padx=20, pady=8)

        # ── Геймификация ──
        ctk.CTkLabel(self, text="🪙 Геймификация", anchor="w",
                     font=("Helvetica", 12, "bold")).pack(fill="x", **pad)

        from ui.tooltip import Tooltip, HelpButton, TIPS
        gami_row = ctk.CTkFrame(self, fg_color="transparent")
        gami_row.pack(fill="x", padx=20, pady=3)
        ctk.CTkLabel(gami_row, text="Включить систему коинов:", anchor="w").pack(side="left")
        HelpButton(gami_row, TIPS["gamification_toggle"]).pack(side="left", padx=(4, 0))
        self.gami_switch = ctk.CTkSwitch(gami_row, text="",
                                          command=self._on_gami_toggle)
        self.gami_switch.pack(side="right")
        if self.settings.gamification_enabled:
            self.gami_switch.select()

        self._gami_details = ctk.CTkFrame(self, fg_color="transparent")
        self._gami_details.pack(fill="x", padx=20)

        neg_row = ctk.CTkFrame(self._gami_details, fg_color="transparent")
        neg_row.pack(fill="x", pady=2)
        ctk.CTkLabel(neg_row, text="Разрешить отрицательный баланс:", anchor="w",
                     font=("Helvetica", 11)).pack(side="left")
        HelpButton(neg_row, TIPS["negative_balance"]).pack(side="left", padx=(4, 0))
        self.neg_switch = ctk.CTkSwitch(neg_row, text="")
        self.neg_switch.pack(side="right")
        if self.settings.allow_negative_balance:
            self.neg_switch.select()

        self._on_gami_toggle()

        # ── Кнопки ──
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

    def _on_gami_toggle(self):
        enabled = self.gami_switch.get()
        state = "normal" if enabled else "disabled"
        for w in self._gami_details.winfo_children():
            for child in w.winfo_children():
                try:
                    child.configure(state=state)
                except Exception:
                    pass
            try:
                w.configure(state=state)
            except Exception:
                pass

    def _save(self):
        try:
            notify_min = int(self.notify_entry.get().strip())
            if notify_min < 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Ошибка", "Введи корректное число минут", parent=self)
            return

        self.settings.overrun_behavior = self.BEHAVIOR_OPTIONS[self.behavior_var.get()]
        self.settings.overrun_source = self.SOURCE_OPTIONS[self.source_var.get()]
        self.settings.notify_before_minutes = notify_min
        self.settings.gamification_enabled = bool(self.gami_switch.get())
        self.settings.allow_negative_balance = bool(self.neg_switch.get())
        storage.save_settings(self.settings.to_db_dict())
        self.on_save(self.settings)
        self.destroy()

