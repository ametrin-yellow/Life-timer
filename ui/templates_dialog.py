import customtkinter as ctk
from tkinter import messagebox
from typing import Callable
import storage
from models import Task


class TemplatesDialog(ctk.CTkToplevel):
    """
    Управление шаблонами ежедневных задач.
    Шаблоны хранятся в ~/.life_timer/templates.json
    """

    def __init__(self, master, on_load: Callable[[list[Task]], None], **kwargs):
        super().__init__(master, **kwargs)
        self.title("📋 Шаблоны задач")
        self.geometry("460x480")
        self.resizable(False, False)
        self.on_load = on_load
        self.templates: list[dict] = storage.load_templates()
        self.after(100, self.lift)
        self.after(100, self.grab_set)
        self._build()

    def _build(self):
        ctk.CTkLabel(self, text="Шаблоны ежедневных задач",
                     font=("Helvetica", 15, "bold")).pack(pady=(14, 4))
        ctk.CTkLabel(self, text="Добавляются в текущий день одним кликом",
                     font=("Helvetica", 11), text_color="gray").pack()

        # Список шаблонов
        self.list_frame = ctk.CTkScrollableFrame(self, height=200, corner_radius=8)
        self.list_frame.pack(fill="x", padx=16, pady=8)
        self._render_list()

        # Форма добавления нового шаблона
        sep = ctk.CTkFrame(self, height=1, fg_color="#333")
        sep.pack(fill="x", padx=16, pady=4)

        ctk.CTkLabel(self, text="Новый шаблон:", anchor="w",
                     font=("Helvetica", 12, "bold")).pack(anchor="w", padx=16)

        form = ctk.CTkFrame(self, fg_color="transparent")
        form.pack(fill="x", padx=16, pady=4)
        self.name_entry = ctk.CTkEntry(form, placeholder_text="Название задачи", width=220)
        self.name_entry.pack(side="left", padx=(0, 6))
        self.min_entry = ctk.CTkEntry(form, placeholder_text="мин", width=60)
        self.min_entry.pack(side="left", padx=(0, 6))
        ctk.CTkButton(form, text="+ Добавить", width=100, height=32,
                      fg_color="#1565C0", corner_radius=6,
                      command=self._add_template).pack(side="left")

        # Кнопки действий
        btns = ctk.CTkFrame(self, fg_color="transparent")
        btns.pack(pady=12)
        ctk.CTkButton(btns, text="Загрузить в день", width=150, height=34,
                      fg_color="#1B5E20", corner_radius=6,
                      command=self._load_to_day).pack(side="left", padx=6)
        ctk.CTkButton(btns, text="Закрыть", width=100, height=34,
                      fg_color="#444", corner_radius=6,
                      command=self.destroy).pack(side="left", padx=6)

    def _render_list(self):
        for w in self.list_frame.winfo_children():
            w.destroy()

        if not self.templates:
            ctk.CTkLabel(self.list_frame, text="Нет шаблонов — добавь ниже",
                         text_color="gray").pack(pady=10)
            return

        for i, tmpl in enumerate(self.templates):
            row = ctk.CTkFrame(self.list_frame, fg_color="#2b2b2b", corner_radius=6)
            row.pack(fill="x", pady=2)
            ctk.CTkLabel(row, text=tmpl["name"],
                         font=("Helvetica", 12, "bold"), anchor="w").pack(side="left", padx=10, pady=6)
            mins = tmpl["allocated_seconds"] // 60
            ctk.CTkLabel(row, text=f"{mins} мин", text_color="gray",
                         font=("Helvetica", 11)).pack(side="left")
            idx = i
            ctk.CTkButton(row, text="✕", width=28, height=28, fg_color="#6D4C41",
                          corner_radius=4,
                          command=lambda i=idx: self._remove(i)).pack(side="right", padx=6)

    def _add_template(self):
        name = self.name_entry.get().strip()
        if not name:
            messagebox.showerror("Ошибка", "Введи название", parent=self)
            return
        try:
            mins = float(self.min_entry.get().strip() or "25")
            if mins <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Ошибка", "Введи корректное время", parent=self)
            return

        self.templates.append({"name": name, "allocated_seconds": int(mins * 60)})
        storage.save_templates(self.templates)
        self.name_entry.delete(0, "end")
        self.min_entry.delete(0, "end")
        self._render_list()

    def _remove(self, idx: int):
        self.templates.pop(idx)
        storage.save_templates(self.templates)
        self._render_list()

    def _load_to_day(self):
        if not self.templates:
            messagebox.showinfo("Шаблоны", "Нет шаблонов для загрузки", parent=self)
            return
        tasks = [Task(name=t["name"], allocated_seconds=t["allocated_seconds"])
                 for t in self.templates]
        self.on_load(tasks)
        messagebox.showinfo("Готово", f"Загружено {len(tasks)} задач в текущий день", parent=self)
        self.destroy()
