import customtkinter as ctk
from storage import get_stats


class StatsPanel(ctk.CTkToplevel):
    """Окно статистики за период."""

    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.title("📊 Статистика")
        self.geometry("520x460")
        self.resizable(False, False)
        self._build()

    def _build(self):
        ctk.CTkLabel(self, text="Статистика за 7 дней",
                     font=("Helvetica", 16, "bold")).pack(pady=(16, 8))

        stats = get_stats(7)
        if not stats:
            ctk.CTkLabel(self, text="Пока нет данных", text_color="gray").pack()
            return

        # Сводка
        summary = ctk.CTkFrame(self, corner_radius=10)
        summary.pack(fill="x", padx=16, pady=6)

        def row(parent, label, value, color="white"):
            f = ctk.CTkFrame(parent, fg_color="transparent")
            f.pack(fill="x", padx=12, pady=2)
            ctk.CTkLabel(f, text=label, font=("Helvetica", 12), text_color="gray",
                         anchor="w").pack(side="left")
            ctk.CTkLabel(f, text=value, font=("Helvetica", 12, "bold"),
                         text_color=color).pack(side="right")

        row(summary, "Всего задач:", str(stats["total_tasks"]))
        row(summary, "Выполнено:", f"{stats['completed_tasks']}  ({stats['completion_rate']}%)",
            "#4CAF50" if stats['completion_rate'] >= 70 else "#FFB74D")
        row(summary, "Запланировано (мин):", str(stats["total_allocated_min"]))
        row(summary, "Потрачено (мин):", str(stats["total_elapsed_min"]))
        row(summary, "Перерасход (мин):", str(stats["total_overrun_min"]),
            "#EF5350" if stats["total_overrun_min"] > 0 else "white")
        row(summary, "Прокрастинация (мин):",
            f"{stats['procrastination_used_min']} / {stats['procrastination_budget_min']}",
            "#FFB74D")

        # Ежедневная таблица
        ctk.CTkLabel(self, text="По дням:", font=("Helvetica", 13, "bold")).pack(
            anchor="w", padx=16, pady=(12, 4))

        table = ctk.CTkScrollableFrame(self, height=180, corner_radius=8)
        table.pack(fill="x", padx=16, pady=4)

        headers = ["Дата", "Задач", "✓", "%", "Перерасход"]
        cols = [0.25, 0.15, 0.1, 0.15, 0.2]
        header_row = ctk.CTkFrame(table, fg_color="transparent")
        header_row.pack(fill="x")
        for h, w in zip(headers, cols):
            ctk.CTkLabel(header_row, text=h, font=("Helvetica", 11, "bold"),
                         text_color="#888").pack(side="left", fill="x",
                         expand=True)

        for d in stats["daily"]:
            r = ctk.CTkFrame(table, fg_color="transparent")
            r.pack(fill="x", pady=1)
            pct = round(d["tasks_completed"] / d["tasks_total"] * 100) if d["tasks_total"] else 0
            for val in [d["date"], str(d["tasks_total"]), str(d["tasks_completed"]),
                        f"{pct}%", f"{d['overrun_min']} мин"]:
                ctk.CTkLabel(r, text=val, font=("Helvetica", 11)).pack(
                    side="left", fill="x", expand=True)

        ctk.CTkButton(self, text="Закрыть", command=self.destroy, width=100).pack(pady=12)
