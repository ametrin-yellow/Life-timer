"""
Статистика — 4 вкладки: День / Неделя / Месяц / Всё время + Геймификация.
Неделя = с понедельника текущей недели.
Месяц = с 1-го числа текущего месяца.
"""
import customtkinter as ctk
from datetime import date, timedelta
from repository import get_stats_summary, get_balance, get_transactions
import repository as repo


def _week_start() -> date:
    today = date.today()
    return today - timedelta(days=today.weekday())   # понедельник


def _month_start() -> date:
    return date.today().replace(day=1)


class StatsPanel(ctk.CTkToplevel):
    """Окно статистики за период."""

    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.title("📊 Статистика")
        self.geometry("560x580")
        self.minsize(480, 460)
        self.resizable(True, True)
        self.after(100, self._force_focus)
        self._build()

    def _force_focus(self):
        self.attributes("-topmost", True)
        self.lift()
        self.focus_force()
        self.after(200, lambda: self.attributes("-topmost", False))

    # ──────────────────────────────────────────────

    def _build(self):
        ctk.CTkLabel(self, text="📊 Статистика",
                     font=("Helvetica", 17, "bold")).pack(pady=(14, 6))

        self.tabview = ctk.CTkTabview(self)
        self.tabview.pack(fill="both", expand=True, padx=14, pady=(0, 4))

        tabs = {
            "📅 День":      (date.today(),    date.today()),
            "📆 Неделя":    (_week_start(),   date.today()),
            "🗓 Месяц":     (_month_start(),  date.today()),
            "🗃 Всё время": (None,            date.today()),
        }

        for tab_name, (d_from, d_to) in tabs.items():
            self.tabview.add(tab_name)
            self._fill_tab(self.tabview.tab(tab_name), tab_name, d_from, d_to)

        # Вкладка геймификации
        settings = repo.get_settings()
        if settings.gamification_enabled:
            self.tabview.add("🪙 Монеты")
            self._fill_gamification_tab(self.tabview.tab("🪙 Монеты"))

        ctk.CTkButton(self, text="Закрыть", command=self.destroy,
                      width=100, fg_color="#444").pack(pady=8)

    # ──────────────────────────────────────────────

    def _fill_tab(self, parent, tab_name: str, date_from, date_to):
        stats = get_stats_summary(date_from=date_from, date_to=date_to)

        if not stats["total_tasks"]:
            ctk.CTkLabel(parent, text="Пока нет данных за этот период",
                         text_color="gray", font=("Helvetica", 13)).pack(expand=True)
            return

        # Подпись периода
        if date_from:
            period_str = (f"{date_from.strftime('%d.%m')} – {date_to.strftime('%d.%m.%Y')}"
                          if date_from != date_to
                          else date_from.strftime('%d.%m.%Y'))
        else:
            period_str = f"всё время по {date_to.strftime('%d.%m.%Y')}"

        ctk.CTkLabel(parent, text=period_str, text_color="gray",
                     font=("Helvetica", 11)).pack(pady=(4, 8))

        # ── Сводка ──
        summary = ctk.CTkFrame(parent, corner_radius=10)
        summary.pack(fill="x", padx=4, pady=(0, 6))

        def row(label, value, color="white"):
            f = ctk.CTkFrame(summary, fg_color="transparent")
            f.pack(fill="x", padx=12, pady=2)
            ctk.CTkLabel(f, text=label, font=("Helvetica", 12),
                         text_color="gray", anchor="w").pack(side="left")
            ctk.CTkLabel(f, text=value, font=("Helvetica", 12, "bold"),
                         text_color=color).pack(side="right")

        cr = stats["completion_rate"]
        row("Всего задач:",    str(stats["total_tasks"]))
        row("Выполнено:",      f"{stats['completed_tasks']}  ({cr}%)",
            "#4CAF50" if cr >= 70 else "#FFB74D")
        row("Пропущено:",      str(stats["skipped_tasks"]), "#EF5350")
        row("Запланировано:",  f"{stats['total_allocated_min']} мин")
        row("Потрачено:",      f"{stats['total_elapsed_min']} мин")
        row("Перерасход:",     f"{stats['total_overrun_min']} мин",
            "#EF5350" if stats["total_overrun_min"] > 0 else "white")
        row("Прокрастинация:",
            f"{stats['procrastination_used_min']} / {stats['procrastination_budget_min']} мин",
            "#FFB74D")

        # ── Таблица по дням (только для периодов > 1 дня) ──
        if tab_name != "📅 День" and stats["daily"]:
            ctk.CTkLabel(parent, text="По дням:",
                         font=("Helvetica", 12, "bold"), anchor="w").pack(
                             fill="x", padx=4, pady=(4, 2))

            table = ctk.CTkScrollableFrame(parent, corner_radius=8, height=160)
            table.pack(fill="x", padx=4)

            hdr = ctk.CTkFrame(table, fg_color="transparent")
            hdr.pack(fill="x")
            for h in ["Дата", "Задач", "✓", "%", "Перерасход"]:
                ctk.CTkLabel(hdr, text=h, font=("Helvetica", 11, "bold"),
                             text_color="#888").pack(side="left", fill="x", expand=True)

            for d in stats["daily"]:
                total = d["tasks_total"]
                done  = d["tasks_completed"]
                pct   = round(done / total * 100) if total else 0
                r = ctk.CTkFrame(table, fg_color="transparent")
                r.pack(fill="x", pady=1)
                for val in [d["date"], str(total), str(done),
                            f"{pct}%", f"{d['overrun_min']} мин"]:
                    ctk.CTkLabel(r, text=val, font=("Helvetica", 11)).pack(
                        side="left", fill="x", expand=True)

    # ──────────────────────────────────────────────

    def _fill_gamification_tab(self, parent):
        """Вкладка с балансом монет, стриком и историей транзакций."""
        try:
            balance = get_balance()
            transactions = get_transactions(limit=50)
        except Exception:
            ctk.CTkLabel(parent, text="Нет данных геймификации",
                         text_color="gray", font=("Helvetica", 13)).pack(expand=True)
            return

        # ── Баланс и стрик ──
        top = ctk.CTkFrame(parent, corner_radius=10, fg_color="#1a1a2e")
        top.pack(fill="x", padx=4, pady=(8, 6))

        balance_frame = ctk.CTkFrame(top, fg_color="transparent")
        balance_frame.pack(side="left", expand=True, padx=20, pady=12)
        ctk.CTkLabel(balance_frame, text="БАЛАНС", font=("Helvetica", 10),
                     text_color="#888").pack()
        bal_color = "#4CAF50" if balance.balance >= 0 else "#EF5350"
        ctk.CTkLabel(balance_frame,
                     text=f"🪙 {balance.balance}",
                     font=("Helvetica", 30, "bold"), text_color=bal_color).pack()

        ctk.CTkFrame(top, width=2, fg_color="#333").pack(side="left", fill="y", pady=10)

        streak_frame = ctk.CTkFrame(top, fg_color="transparent")
        streak_frame.pack(side="left", expand=True, padx=20, pady=12)
        ctk.CTkLabel(streak_frame, text="СЕРИЯ", font=("Helvetica", 10),
                     text_color="#888").pack()
        streak_icon = "🔥" if balance.streak > 0 else "❄"
        streak_color = "#FFB74D" if balance.streak > 0 else "#90A4AE"
        ctk.CTkLabel(streak_frame,
                     text=f"{streak_icon} {balance.streak} дн.",
                     font=("Helvetica", 30, "bold"), text_color=streak_color).pack()
        if balance.streak >= 10:
            ctk.CTkLabel(streak_frame, text="×2.0 множитель!",
                         font=("Helvetica", 10), text_color="#4CAF50").pack()
        elif balance.streak > 0:
            mult = 1.0 + 0.1 * min(balance.streak, 10)
            ctk.CTkLabel(streak_frame, text=f"×{mult:.1f} множитель",
                         font=("Helvetica", 10), text_color="#888").pack()

        # ── Список транзакций ──
        ctk.CTkLabel(parent, text="История транзакций:",
                     font=("Helvetica", 12, "bold"), anchor="w").pack(
                         fill="x", padx=4, pady=(6, 2))

        if not transactions:
            ctk.CTkLabel(parent, text="Пока нет транзакций",
                         text_color="gray", font=("Helvetica", 12)).pack(pady=10)
            return

        table = ctk.CTkScrollableFrame(parent, corner_radius=8)
        table.pack(fill="both", expand=True, padx=4, pady=(0, 4))

        # Заголовок
        hdr = ctk.CTkFrame(table, fg_color="#1a1a1a")
        hdr.pack(fill="x", pady=(0, 2))
        ctk.CTkLabel(hdr, text="Дата", font=("Helvetica", 11, "bold"),
                     text_color="#888", width=90).pack(side="left", padx=4, pady=3)
        ctk.CTkLabel(hdr, text="Описание", font=("Helvetica", 11, "bold"),
                     text_color="#888", anchor="w").pack(side="left", fill="x", expand=True)
        ctk.CTkLabel(hdr, text="Монеты", font=("Helvetica", 11, "bold"),
                     text_color="#888", width=70).pack(side="right", padx=4)

        for tx in transactions:
            row_fg = "#2a2a2a" if transactions.index(tx) % 2 == 0 else "#222"
            r = ctk.CTkFrame(table, fg_color=row_fg, corner_radius=4)
            r.pack(fill="x", pady=1)

            date_str = tx.created_at.strftime("%d.%m %H:%M") if tx.created_at else "—"
            ctk.CTkLabel(r, text=date_str, font=("Helvetica", 11),
                         text_color="#888", width=90).pack(side="left", padx=4, pady=3)
            ctk.CTkLabel(r, text=tx.reason, font=("Helvetica", 11),
                         anchor="w").pack(side="left", fill="x", expand=True)
            amount_color = "#4CAF50" if tx.amount > 0 else "#EF5350"
            amount_text = f"+{tx.amount}" if tx.amount > 0 else str(tx.amount)
            ctk.CTkLabel(r, text=f"🪙 {amount_text}", font=("Helvetica", 11, "bold"),
                         text_color=amount_color, width=70).pack(side="right", padx=4)

