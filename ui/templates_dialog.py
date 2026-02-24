import customtkinter as ctk
from tkinter import messagebox
from typing import Callable
import repository as storage

CATEGORIES = [
    "🌙 Сон и отдых", "🚿 Гигиена", "🍳 Еда",
    "🏃 Активность", "🧘 Ментальное", "🏠 Быт"
]
BUILTIN_PRESETS = {
    "💼 Рабочий день": ["Сон", "Утренние ритуалы", "Завтрак", "Обед", "Ужин", "Вечерние ритуалы"],
    "🛋 Выходной":     ["Сон", "Утренние ритуалы", "Завтрак", "Прогулка", "Обед",
                        "Дневной сон", "Ужин", "Вечерние ритуалы"],
}


class _TmplCompat:
    def get_all_templates(self):
        grouped = {cat: [] for cat in CATEGORIES}
        grouped["👤 Мои шаблоны"] = []
        for t in storage.get_templates_as_dicts():
            cat = t.get("category", "👤 Мои шаблоны")
            grouped.setdefault(cat, []).append(t)
        return {k: v for k, v in grouped.items() if v}

    def resolve_preset(self, preset_name):
        flat = {t["name"]: t for group in self.get_all_templates().values() for t in group}
        names = BUILTIN_PRESETS.get(preset_name, [])
        for p in storage.get_user_presets_as_dicts():
            if p["name"] == preset_name:
                names = p["templates"]
                break
        return [flat[n] for n in names if n in flat]


tmpl = _TmplCompat()
from adapter import Task


class TemplatesDialog(ctk.CTkToplevel):

    def __init__(self, master, on_load: Callable[[list[Task]], None], **kwargs):
        super().__init__(master, **kwargs)
        self.title("📋 Шаблоны и пресеты")
        self.geometry("580x580")
        self.resizable(False, True)
        self.on_load = on_load
        self.after(100, self._force_focus)
        self.after(150, self.grab_set)
        self._build()

    def _force_focus(self):
        self.attributes("-topmost", True)
        self.lift()
        self.focus_force()
        self.after(200, lambda: self.attributes("-topmost", False))

    def _build(self):
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
        # Очищаем перед перестройкой
        for w in parent.winfo_children():
            w.destroy()

        ctk.CTkLabel(parent, text="Загрузить готовый набор задач в текущий день",
                     text_color="gray", font=("Helvetica", 11)).pack(pady=(6, 8))

        scroll = ctk.CTkScrollableFrame(parent, corner_radius=0, fg_color="transparent")
        scroll.pack(fill="both", expand=True)

        # Встроенные пресеты
        for preset_name in BUILTIN_PRESETS:
            self._preset_row(scroll, preset_name, builtin=True)

        # Пользовательские
        user_presets = storage.get_user_presets_as_dicts()
        for p in user_presets:
            self._preset_row(scroll, p["name"], builtin=False)

        ctk.CTkButton(parent, text="+ Создать свой пресет", width=180, height=32,
                      fg_color="#1565C0", corner_radius=6,
                      command=self._create_preset).pack(pady=(10, 0))

    def _preset_row(self, parent, preset_name: str, builtin: bool):
        tasks = tmpl.resolve_preset(preset_name)
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
                     font=("Helvetica", 10), anchor="w", wraplength=330).pack(anchor="w")
        ctk.CTkLabel(info, text=f"⏱ {time_str}", text_color="#FFB74D",
                     font=("Helvetica", 11)).pack(anchor="w")

        btns = ctk.CTkFrame(row, fg_color="transparent")
        btns.pack(side="right", padx=8)

        ctk.CTkButton(btns, text="Загрузить", width=88, height=30,
                      fg_color="#1B5E20", corner_radius=6,
                      command=lambda p=preset_name: self._load_preset(p)).pack(pady=2)

        if not builtin:
            ctk.CTkButton(btns, text="✎ Изменить", width=88, height=26,
                          fg_color="#1565C0", corner_radius=6,
                          command=lambda p=preset_name: self._edit_preset(p)).pack(pady=2)
            ctk.CTkButton(btns, text="✕ Удалить", width=88, height=26,
                          fg_color="#4a1010", corner_radius=6,
                          command=lambda p=preset_name: self._delete_preset(p)).pack(pady=2)

    # ──────────────────────────────────────────────
    #  Вкладка шаблонов
    # ──────────────────────────────────────────────

    def _build_templates_tab(self, parent):
        for w in parent.winfo_children():
            w.destroy()

        scroll = ctk.CTkScrollableFrame(parent, corner_radius=0, fg_color="transparent")
        scroll.pack(fill="both", expand=True)

        grouped = tmpl.get_all_templates()
        for category, items in grouped.items():
            ctk.CTkLabel(scroll, text=category,
                         font=("Helvetica", 12, "bold"), anchor="w").pack(
                             fill="x", padx=4, pady=(10, 2))
            for t in items:
                self._template_row(scroll, t)

        # Форма добавления
        ctk.CTkFrame(scroll, height=1, fg_color="#444").pack(fill="x", pady=10)
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

    def _template_row(self, parent, t: dict):
        row = ctk.CTkFrame(parent, corner_radius=6, fg_color="#2b2b2b")
        row.pack(fill="x", pady=2)

        mins = t["allocated_seconds"] // 60
        h, m = divmod(mins, 60)
        time_str = f"{h}ч {m}мин" if h else f"{m}мин"

        ctk.CTkLabel(row, text=t["name"],
                     font=("Helvetica", 12), anchor="w").pack(side="left", padx=10, pady=6)
        ctk.CTkLabel(row, text=time_str, text_color="#FFB74D",
                     font=("Helvetica", 11)).pack(side="left", padx=4)

        btn_frame = ctk.CTkFrame(row, fg_color="transparent")
        btn_frame.pack(side="right", padx=6)

        ctk.CTkButton(btn_frame, text="+ В день", width=80, height=26,
                      fg_color="#1B5E20", corner_radius=5,
                      command=lambda t=t: self._load_single(t)).pack(side="left", padx=2)

        if not t.get("builtin"):
            ctk.CTkButton(btn_frame, text="✎", width=28, height=26,
                          fg_color="#1565C0", corner_radius=5,
                          command=lambda t=t: self._edit_user_template(t)).pack(
                              side="left", padx=2)
            ctk.CTkButton(btn_frame, text="✕", width=28, height=26,
                          fg_color="#4a1010", corner_radius=5,
                          command=lambda t=t: self._delete_user_template(t)).pack(
                              side="left", padx=2)

    # ──────────────────────────────────────────────
    #  Действия — пресеты
    # ──────────────────────────────────────────────

    def _load_preset(self, preset_name: str):
        tasks_data = tmpl.resolve_preset(preset_name)
        tasks = [Task(name=t["name"], allocated_seconds=t["allocated_seconds"])
                 for t in tasks_data]
        self.on_load(tasks)
        messagebox.showinfo("Готово", f"Загружено {len(tasks)} задач из «{preset_name}»",
                            parent=self)
        self.destroy()

    def _create_preset(self):
        EditPresetDialog(self, preset_name=None, on_save=self._save_new_preset)

    def _save_new_preset(self, name: str, template_names: list[str]):
        presets = storage.get_user_presets_as_dicts()
        presets.append({"name": name, "templates": template_names})
        storage.save_user_presets_compat(presets)
        self._build_presets_tab(self.tabview.tab("🗂 Пресеты"))

    def _edit_preset(self, preset_name: str):
        EditPresetDialog(self, preset_name=preset_name,
                         on_save=lambda name, tpls: self._save_edited_preset(
                             preset_name, name, tpls))

    def _save_edited_preset(self, old_name: str, new_name: str, template_names: list[str]):
        presets = storage.get_user_presets_as_dicts()
        presets = [p for p in presets if p["name"] != old_name]
        presets.append({"name": new_name, "templates": template_names})
        storage.save_user_presets_compat(presets)
        self._build_presets_tab(self.tabview.tab("🗂 Пресеты"))

    def _delete_preset(self, preset_name: str):
        if not messagebox.askyesno("Удалить пресет",
                                   f"Удалить пресет «{preset_name}»?", parent=self):
            return
        presets = [p for p in storage.get_user_presets_as_dicts()
                   if p["name"] != preset_name]
        storage.save_user_presets_compat(presets)
        self._build_presets_tab(self.tabview.tab("🗂 Пресеты"))

    # ──────────────────────────────────────────────
    #  Действия — шаблоны
    # ──────────────────────────────────────────────

    def _load_single(self, t: dict):
        self.on_load([Task(name=t["name"], allocated_seconds=t["allocated_seconds"])])
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
        storage.add_user_template(name, int(mins * 60), self.new_cat.get())
        self._build_templates_tab(self.tabview.tab("📋 Шаблоны"))

    def _edit_user_template(self, t: dict):
        EditTemplateDialog(self, t, on_save=self._save_edited_template)

    def _save_edited_template(self, old_t: dict, new_name: str,
                               new_mins: float, new_cat: str):
        # Удаляем старый, добавляем новый
        storage.delete_user_template(old_t["id"])
        storage.add_user_template(new_name, int(new_mins * 60), new_cat)
        self._build_templates_tab(self.tabview.tab("📋 Шаблоны"))

    def _delete_user_template(self, t: dict):
        if not messagebox.askyesno("Удалить шаблон",
                                   f"Удалить шаблон «{t['name']}»?", parent=self):
            return
        storage.delete_user_template(t["id"])
        self._build_templates_tab(self.tabview.tab("📋 Шаблоны"))


# ──────────────────────────────────────────────
#  Диалог создания/редактирования пресета
# ──────────────────────────────────────────────

class EditPresetDialog(ctk.CTkToplevel):

    def __init__(self, master, preset_name: str | None,
                 on_save: Callable[[str, list[str]], None], **kwargs):
        super().__init__(master, **kwargs)
        self.title("Редактировать пресет" if preset_name else "Новый пресет")
        self.geometry("440x500")
        self.resizable(False, False)
        self.on_save = on_save
        self.checks: dict[str, ctk.BooleanVar] = {}

        # Предзаполнение при редактировании — берём имена шаблонов из БД
        selected_now: set[str] = set()
        if preset_name:
            for p in storage.get_user_presets_as_dicts():
                if p["name"] == preset_name:
                    selected_now = set(p["templates"])
                    break

        self.transient(master)
        self.after(100, self._force_focus)
        self.after(200, self.grab_set)
        self._build(preset_name or "", selected_now)

    def _force_focus(self):
        self.attributes("-topmost", True)
        self.lift()
        self.focus_force()
        self.after(200, lambda: self.attributes("-topmost", False))

    def _build(self, initial_name: str, selected: set):
        ctk.CTkLabel(self, text="Название пресета:", anchor="w").pack(
            fill="x", padx=16, pady=(14, 4))
        self.name_entry = ctk.CTkEntry(self, placeholder_text="например: Спортивный день")
        self.name_entry.pack(fill="x", padx=16)
        if initial_name:
            self.name_entry.insert(0, initial_name)

        ctk.CTkLabel(self, text="Выбери шаблоны:", anchor="w",
                     font=("Helvetica", 12, "bold")).pack(fill="x", padx=16, pady=(12, 4))

        scroll = ctk.CTkScrollableFrame(self, height=300, corner_radius=8)
        scroll.pack(fill="x", padx=16)

        for category, items in tmpl.get_all_templates().items():
            ctk.CTkLabel(scroll, text=category, font=("Helvetica", 11, "bold"),
                         text_color="gray").pack(anchor="w", padx=4, pady=(6, 2))
            for t in items:
                var = ctk.BooleanVar(value=t["name"] in selected)
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
        ctk.CTkButton(btns, text="Сохранить", width=120, fg_color="#1B5E20",
                      command=self._save).pack(side="left", padx=6)

    def _save(self):
        from tkinter import messagebox as mb
        name = self.name_entry.get().strip()
        if not name:
            mb.showerror("Ошибка", "Введи название пресета", parent=self)
            return
        selected = [n for n, v in self.checks.items() if v.get()]
        if not selected:
            mb.showerror("Ошибка", "Выбери хотя бы один шаблон", parent=self)
            return
        self.on_save(name, selected)
        self.destroy()


# ──────────────────────────────────────────────
#  Диалог редактирования шаблона
# ──────────────────────────────────────────────

class EditTemplateDialog(ctk.CTkToplevel):

    def __init__(self, master, t: dict,
                 on_save: Callable, **kwargs):
        super().__init__(master, **kwargs)
        self.title("Редактировать шаблон")
        self.geometry("380x220")
        self.resizable(False, False)
        self.t = t
        self.on_save = on_save
        self.transient(master)
        self.after(100, self._force_focus)
        self.after(200, self.grab_set)
        self._build()

    def _force_focus(self):
        self.attributes("-topmost", True)
        self.lift()
        self.focus_force()
        self.after(200, lambda: self.attributes("-topmost", False))

    def _build(self):
        pad = {"padx": 16, "pady": 4}

        ctk.CTkLabel(self, text="Название:", anchor="w").pack(fill="x", **pad)
        self.name_e = ctk.CTkEntry(self)
        self.name_e.insert(0, self.t["name"])
        self.name_e.pack(fill="x", padx=16)

        ctk.CTkLabel(self, text="Время (мин):", anchor="w").pack(fill="x", **pad)
        self.mins_e = ctk.CTkEntry(self)
        self.mins_e.insert(0, str(self.t["allocated_seconds"] // 60))
        self.mins_e.pack(fill="x", padx=16)

        ctk.CTkLabel(self, text="Категория:", anchor="w").pack(fill="x", **pad)
        cat_options = CATEGORIES + ["👤 Мои шаблоны"]
        self.cat_menu = ctk.CTkOptionMenu(self, values=cat_options)
        current_cat = self.t.get("category", "👤 Мои шаблоны")
        self.cat_menu.set(current_cat if current_cat in cat_options else "👤 Мои шаблоны")
        self.cat_menu.pack(fill="x", padx=16)

        btns = ctk.CTkFrame(self, fg_color="transparent")
        btns.pack(pady=12)
        ctk.CTkButton(btns, text="Отмена", width=100, fg_color="#444",
                      command=self.destroy).pack(side="left", padx=6)
        ctk.CTkButton(btns, text="Сохранить", width=120, fg_color="#1B5E20",
                      command=self._save).pack(side="left", padx=6)

    def _save(self):
        from tkinter import messagebox as mb
        name = self.name_e.get().strip()
        if not name:
            mb.showerror("Ошибка", "Введи название", parent=self)
            return
        try:
            mins = float(self.mins_e.get().strip())
            if mins <= 0:
                raise ValueError
        except ValueError:
            mb.showerror("Ошибка", "Введи корректное время", parent=self)
            return
        self.on_save(self.t, name, mins, self.cat_menu.get())
        self.destroy()
