import customtkinter as ctk
from tkinter import messagebox, simpledialog
from typing import Callable
import storage
import templates as tmpl
from models import Task
from templates import CATEGORIES, BUILTIN_PRESETS


class TemplatesDialog(ctk.CTkToplevel):

    def __init__(self, master, on_load: Callable[[list[Task]], None], **kwargs):
        super().__init__(master, **kwargs)
        self.title("📋 Шаблоны и пресеты")
        self.geometry("560x560")
        self.resizable(False, True)
        self.on_load = on_load
        self.user_templates: list[dict] = storage.load_templates()
        self.after(100, self._force_focus)
        self.after(150, self.grab_set)
        self._build()

    def _force_focus(self):
        self.attributes("-topmost", True)
        self.lift()
        self.focus_force()
        self.after(200, lambda: self.attributes("-topmost", False))

    def _build(self):
        # Вкладки: Пресеты / Шаблоны
        self.tabview = ctk.CTkTabview(self)
        self.tabview.pack(fill="both", expand=True, padx=12, pady=(10, 4))
        self.tabview.add("🗂 Пресеты")
        self.tabview.add("📋 Шаблоны")

        self._build_presets_tab(self.tabview.tab("🗂 Пресеты"))
        self._build_templates_tab(self.tabview.tab("📋 Шаблоны"))

        ctk.CTkButton(self, text="Закрыть", width=100, fg_color="#444",
                      command=self.destroy).pack(pady=8)

    # ──────────────────────────────────────────────
    #  Вкладка пресетов
    # ──────────────────────────────────────────────

    def _build_presets_tab(self, parent):
        ctk.CTkLabel(parent, text="Загрузить готовый набор задач в текущий день",
                     text_color="gray", font=("Helvetica", 11)).pack(pady=(6, 10))

        all_presets = dict(BUILTIN_PRESETS)
        # Пользовательские пресеты
        for p in storage.load_user_presets():
            all_presets[p["name"]] = p["templates"]

        for preset_name in all_presets:
            tasks = tmpl.resolve_preset(preset_name, self.user_templates)
            total_min = sum(t["allocated_seconds"] for t in tasks) // 60
            h, m = divmod(total_min, 60)
            time_str = f"{h}ч {m}мин" if h else f"{m}мин"

            row = ctk.CTkFrame(parent, corner_radius=8, fg_color="#2b2b2b")
            row.pack(fill="x", pady=3)

            info = ctk.CTkFrame(row, fg_color="transparent")
            info.pack(side="left", fill="both", expand=True, padx=10, pady=8)
            ctk.CTkLabel(info, text=preset_name,
                         font=("Helvetica", 13, "bold"), anchor="w").pack(anchor="w")
            task_names = ", ".join(t["name"] for t in tasks)
            ctk.CTkLabel(info, text=task_names, text_color="gray",
                         font=("Helvetica", 10), anchor="w", wraplength=340).pack(anchor="w")
            ctk.CTkLabel(info, text=f"⏱ {time_str}", text_color="#FFB74D",
                         font=("Helvetica", 11)).pack(anchor="w")

            ctk.CTkButton(row, text="Загрузить", width=90, height=32,
                          fg_color="#1B5E20", corner_radius=6,
                          command=lambda p=preset_name: self._load_preset(p)).pack(
                              side="right", padx=8)

        # Кнопка создать свой пресет
        ctk.CTkButton(parent, text="+ Создать свой пресет", width=180, height=32,
                      fg_color="#1565C0", corner_radius=6,
                      command=self._create_preset).pack(pady=(12, 0))

    # ──────────────────────────────────────────────
    #  Вкладка шаблонов
    # ──────────────────────────────────────────────

    def _build_templates_tab(self, parent):
        scroll = ctk.CTkScrollableFrame(parent, corner_radius=0, fg_color="transparent")
        scroll.pack(fill="both", expand=True)

        grouped = tmpl.get_all_templates(self.user_templates)

        for category, items in grouped.items():
            ctk.CTkLabel(scroll, text=category,
                         font=("Helvetica", 12, "bold"), anchor="w").pack(
                             fill="x", padx=4, pady=(10, 2))

            for t in items:
                row = ctk.CTkFrame(scroll, corner_radius=6, fg_color="#2b2b2b")
                row.pack(fill="x", pady=2)

                mins = t["allocated_seconds"] // 60
                h, m = divmod(mins, 60)
                time_str = f"{h}ч {m}мин" if h else f"{m}мин"

                ctk.CTkLabel(row, text=t["name"],
                             font=("Helvetica", 12), anchor="w").pack(
                                 side="left", padx=10, pady=6)
                ctk.CTkLabel(row, text=time_str, text_color="#FFB74D",
                             font=("Helvetica", 11)).pack(side="left", padx=4)

                btn_frame = ctk.CTkFrame(row, fg_color="transparent")
                btn_frame.pack(side="right", padx=6)

                ctk.CTkButton(btn_frame, text="+ В день", width=80, height=26,
                              fg_color="#1B5E20", corner_radius=5,
                              command=lambda t=t: self._load_single(t)).pack(
                                  side="left", padx=2)

                if not t.get("builtin"):
                    ctk.CTkButton(btn_frame, text="✕", width=28, height=26,
                                  fg_color="#4a1010", corner_radius=5,
                                  command=lambda t=t: self._delete_user_template(t)).pack(
                                      side="left", padx=2)

        # Форма добавления
        sep = ctk.CTkFrame(scroll, height=1, fg_color="#444")
        sep.pack(fill="x", pady=10)
        ctk.CTkLabel(scroll, text="Добавить свой шаблон:",
                     font=("Helvetica", 12, "bold"), anchor="w").pack(fill="x", padx=4)

        form = ctk.CTkFrame(scroll, fg_color="transparent")
        form.pack(fill="x", pady=4)

        self.new_name = ctk.CTkEntry(form, placeholder_text="Название", width=160)
        self.new_name.pack(side="left", padx=(0, 4))
        self.new_mins = ctk.CTkEntry(form, placeholder_text="мин", width=60)
        self.new_mins.pack(side="left", padx=(0, 4))

        cat_options = CATEGORIES + ["👤 Мои шаблоны"]
        self.new_cat = ctk.CTkOptionMenu(form, values=cat_options, width=160)
        self.new_cat.set("👤 Мои шаблоны")
        self.new_cat.pack(side="left", padx=(0, 4))

        ctk.CTkButton(form, text="+ Добавить", width=90, height=32,
                      fg_color="#1565C0", corner_radius=6,
                      command=self._add_user_template).pack(side="left")

    # ──────────────────────────────────────────────
    #  Действия
    # ──────────────────────────────────────────────

    def _load_preset(self, preset_name: str):
        tasks_data = tmpl.resolve_preset(preset_name, self.user_templates)
        tasks = [Task(name=t["name"], allocated_seconds=t["allocated_seconds"])
                 for t in tasks_data]
        self.on_load(tasks)
        messagebox.showinfo("Готово", f"Загружено {len(tasks)} задач из «{preset_name}»",
                            parent=self)
        self.destroy()

    def _load_single(self, t: dict):
        task = Task(name=t["name"], allocated_seconds=t["allocated_seconds"])
        self.on_load([task])
        self.destroy()

    def _add_user_template(self):
        name = self.new_name.get().strip()
        if not name:
            messagebox.showerror("Ошибка", "Введи название", parent=self)
            return
        try:
            mins = float(self.new_mins.get().strip() or "30")
            if mins <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Ошибка", "Введи корректное время", parent=self)
            return

        self.user_templates.append({
            "name": name,
            "allocated_seconds": int(mins * 60),
            "category": self.new_cat.get(),
        })
        storage.save_templates(self.user_templates)
        # Перестраиваем вкладку
        for w in self.tabview.tab("📋 Шаблоны").winfo_children():
            w.destroy()
        self._build_templates_tab(self.tabview.tab("📋 Шаблоны"))

    def _delete_user_template(self, t: dict):
        self.user_templates = [u for u in self.user_templates if u["name"] != t["name"]]
        storage.save_templates(self.user_templates)
        for w in self.tabview.tab("📋 Шаблоны").winfo_children():
            w.destroy()
        self._build_templates_tab(self.tabview.tab("📋 Шаблоны"))

    def _create_preset(self):
        """Создать пресет из выбранных шаблонов."""
        CreatePresetDialog(self, self.user_templates, on_save=self._save_preset)

    def _save_preset(self, name: str, template_names: list[str]):
        presets = storage.load_user_presets()
        presets.append({"name": name, "templates": template_names})
        storage.save_user_presets(presets)
        # Перестраиваем вкладку пресетов
        for w in self.tabview.tab("🗂 Пресеты").winfo_children():
            w.destroy()
        self._build_presets_tab(self.tabview.tab("🗂 Пресеты"))


class CreatePresetDialog(ctk.CTkToplevel):
    """Диалог создания своего пресета."""

    def __init__(self, master, user_templates: list[dict],
                 on_save: Callable[[str, list[str]], None], **kwargs):
        super().__init__(master, **kwargs)
        self.title("Новый пресет")
        self.geometry("420x480")
        self.resizable(False, False)
        self.user_templates = user_templates
        self.on_save = on_save
        self.checks: dict[str, ctk.BooleanVar] = {}
        self.after(100, self._force_focus)
        self.after(150, self.grab_set)
        self._build()

    def _force_focus(self):
        self.attributes("-topmost", True)
        self.lift()
        self.focus_force()
        self.after(200, lambda: self.attributes("-topmost", False))

    def _build(self):
        ctk.CTkLabel(self, text="Название пресета:", anchor="w").pack(
            fill="x", padx=16, pady=(14, 4))
        self.name_entry = ctk.CTkEntry(self, placeholder_text="например: Спортивный день")
        self.name_entry.pack(fill="x", padx=16)

        ctk.CTkLabel(self, text="Выбери шаблоны:", anchor="w",
                     font=("Helvetica", 12, "bold")).pack(fill="x", padx=16, pady=(12, 4))

        scroll = ctk.CTkScrollableFrame(self, height=280, corner_radius=8)
        scroll.pack(fill="x", padx=16)

        grouped = tmpl.get_all_templates(self.user_templates)
        for category, items in grouped.items():
            ctk.CTkLabel(scroll, text=category, font=("Helvetica", 11, "bold"),
                         text_color="gray").pack(anchor="w", padx=4, pady=(6, 2))
            for t in items:
                var = ctk.BooleanVar(value=False)
                self.checks[t["name"]] = var
                mins = t["allocated_seconds"] // 60
                h, m = divmod(mins, 60)
                time_str = f"{h}ч {m}м" if h else f"{m}м"
                ctk.CTkCheckBox(scroll, text=f"{t['name']}  ({time_str})",
                                variable=var).pack(anchor="w", padx=8, pady=1)

        btns = ctk.CTkFrame(self, fg_color="transparent")
        btns.pack(pady=12)
        ctk.CTkButton(btns, text="Отмена", width=100, fg_color="#444",
                      command=self.destroy).pack(side="left", padx=6)
        ctk.CTkButton(btns, text="Создать", width=120, fg_color="#1B5E20",
                      command=self._save).pack(side="left", padx=6)

    def _save(self):
        name = self.name_entry.get().strip()
        if not name:
            messagebox.showerror("Ошибка", "Введи название пресета", parent=self)
            return
        selected = [n for n, v in self.checks.items() if v.get()]
        if not selected:
            messagebox.showerror("Ошибка", "Выбери хотя бы один шаблон", parent=self)
            return
        self.on_save(name, selected)
        self.destroy()
