import customtkinter as ctk
from typing import Optional
from adapter import DayPlan, Task
from ui.task_panel import fmt_time


class TimerHeader(ctk.CTkFrame):
    """
    Верхняя панель: активный таймер + счётчик прокрастинации + баланс коинов.
    """

    def __init__(self, master, plan: DayPlan, active_task_id: Optional[str],
                 proc_remaining: int, proc_overrun: int,
                 gamification_enabled: bool = False,
                 coin_balance: int = 0, coin_streak: int = 0,
                 **kwargs):
        super().__init__(master, **kwargs)
        self.plan = plan
        self.active_task_id = active_task_id
        self.proc_remaining = proc_remaining
        self.proc_overrun = proc_overrun
        self.gamification_enabled = gamification_enabled
        self.coin_balance = coin_balance
        self.coin_streak = coin_streak
        self._build()

    def _build(self):
        from ui.tooltip import Tooltip, HelpButton, TIPS
        self.configure(corner_radius=12, fg_color="#1a1a2e")

        # Активная задача
        task_block = ctk.CTkFrame(self, fg_color="transparent")
        task_block.pack(side="left", fill="both", expand=True, padx=16, pady=12)
        ctk.CTkLabel(task_block, text="СЕЙЧАС", font=("Helvetica", 10),
                     text_color="#888").pack(anchor="w")
        self.task_name_lbl = ctk.CTkLabel(task_block, text="— прокрастинация —",
                                           font=("Helvetica", 15, "bold"), text_color="#FFB74D")
        self.task_name_lbl.pack(anchor="w")
        self.task_timer_lbl = ctk.CTkLabel(task_block, text="",
                                            font=("Helvetica", 36, "bold"), text_color="#4FC3F7")
        self.task_timer_lbl.pack(anchor="w")

        # Прокрастинация
        ctk.CTkFrame(self, width=2, fg_color="#333").pack(side="left", fill="y", pady=10)
        proc_block = ctk.CTkFrame(self, fg_color="transparent")
        proc_block.pack(side="left", fill="both", padx=16, pady=12)

        proc_title_row = ctk.CTkFrame(proc_block, fg_color="transparent")
        proc_title_row.pack(anchor="w")
        ctk.CTkLabel(proc_title_row, text="ПРОКРАСТИНАЦИЯ", font=("Helvetica", 10),
                     text_color="#888").pack(side="left")
        HelpButton(proc_title_row, TIPS["procrastination"]).pack(side="left", padx=(4, 0))

        ctk.CTkLabel(proc_block, text="осталось", font=("Helvetica", 10),
                     text_color="#555").pack(anchor="w")
        self.proc_remaining_lbl = ctk.CTkLabel(proc_block, text="",
                                                font=("Helvetica", 24, "bold"), text_color="#FFB74D")
        self.proc_remaining_lbl.pack(anchor="w")
        Tooltip(self.proc_remaining_lbl, TIPS["procrastination"])
        self.proc_status_lbl = ctk.CTkLabel(proc_block, text="",
                                             font=("Helvetica", 10), text_color="#888")
        self.proc_status_lbl.pack(anchor="w")

        # Монеты
        if self.gamification_enabled:
            ctk.CTkFrame(self, width=2, fg_color="#333").pack(side="left", fill="y", pady=10)
            coins_block = ctk.CTkFrame(self, fg_color="transparent")
            coins_block.pack(side="left", fill="both", padx=16, pady=12)

            coins_title_row = ctk.CTkFrame(coins_block, fg_color="transparent")
            coins_title_row.pack(anchor="w")
            ctk.CTkLabel(coins_title_row, text="МОНЕТЫ", font=("Helvetica", 10),
                         text_color="#888").pack(side="left")
            HelpButton(coins_title_row, TIPS["coins_balance"]).pack(side="left", padx=(4, 0))

            balance_color = "#4CAF50" if self.coin_balance >= 0 else "#EF5350"
            self.coins_lbl = ctk.CTkLabel(
                coins_block,
                text=f"🪙 {self.coin_balance:+d}" if self.coin_balance != 0 else "🪙 0",
                font=("Helvetica", 24, "bold"), text_color=balance_color)
            self.coins_lbl.pack(anchor="w")
            Tooltip(self.coins_lbl, TIPS["coins_balance"])

            streak_text = f"🔥 {self.coin_streak} дн." if self.coin_streak > 0 else "❄ нет серии"
            streak_color = "#FFB74D" if self.coin_streak > 0 else "#555"
            self.streak_lbl = ctk.CTkLabel(coins_block, text=streak_text,
                                            font=("Helvetica", 11), text_color=streak_color)
            self.streak_lbl.pack(anchor="w")
            Tooltip(self.streak_lbl, TIPS["coins_streak"])

            self.preview_lbl = ctk.CTkLabel(coins_block, text="",
                                             font=("Helvetica", 10), text_color="#888")
            self.preview_lbl.pack(anchor="w")
            Tooltip(self.preview_lbl, TIPS["coins_preview"])
            self._refresh_coin_preview()
        else:
            self.coins_lbl = None
            self.streak_lbl = None
            self.preview_lbl = None

        self._refresh_display()

    def _refresh_display(self):
        task = self._get_active_task()
        if task:
            self.task_name_lbl.configure(text=task.name, text_color="white")
            if task.is_overrun:
                self.task_timer_lbl.configure(text=f"-{fmt_time(task.overrun_seconds)}",
                                               text_color="#EF5350")
            else:
                self.task_timer_lbl.configure(text=fmt_time(task.remaining_seconds),
                                               text_color="#4FC3F7")
        else:
            self.task_name_lbl.configure(text="— прокрастинация —", text_color="#FFB74D")
            self.task_timer_lbl.configure(text="", text_color="#4FC3F7")

        if self.proc_overrun > 0:
            self.proc_remaining_lbl.configure(text=f"-{fmt_time(self.proc_overrun)}",
                                               text_color="#EF5350")
            self.proc_status_lbl.configure(text="лимит исчерпан ⚠", text_color="#EF5350")
        else:
            self.proc_remaining_lbl.configure(text=fmt_time(self.proc_remaining),
                                               text_color="#FFB74D")
            self.proc_status_lbl.configure(
                text=f"потрачено: {fmt_time(self.plan.procrastination_used)}", text_color="#555")

        if self.coins_lbl:
            balance_color = "#4CAF50" if self.coin_balance >= 0 else "#EF5350"
            self.coins_lbl.configure(
                text=f"🪙 {self.coin_balance:+d}" if self.coin_balance != 0 else "🪙 0",
                text_color=balance_color)
        if self.streak_lbl:
            streak_text = f"🔥 {self.coin_streak} дн." if self.coin_streak > 0 else "❄ нет серии"
            self.streak_lbl.configure(
                text=streak_text,
                text_color="#FFB74D" if self.coin_streak > 0 else "#555")
        self._refresh_coin_preview()

    def _refresh_coin_preview(self):
        if not self.preview_lbl:
            return
        try:
            from datetime import date as _date
            import gamification as gami
            preview = gami.calc_day_preview(_date.today())
            if preview:
                pot = preview["total_potential"]
                earn = preview["total_earned"]
                text = (f"сегодня: {earn:+d} / потенциал: {pot:+d}"
                        if earn != 0 else f"потенциал сегодня: {pot:+d}")
                self.preview_lbl.configure(
                    text=text, text_color="#4CAF50" if pot >= 0 else "#EF5350")
            else:
                self.preview_lbl.configure(text="")
        except Exception:
            self.preview_lbl.configure(text="")

    def _get_active_task(self) -> Optional[Task]:
        if not self.active_task_id:
            return None
        for t in self.plan.tasks:
            if t.id == self.active_task_id:
                return t
        return None

    def refresh(self, plan: DayPlan, active_task_id: Optional[str],
                proc_remaining: int, proc_overrun: int,
                coin_balance: int = 0, coin_streak: int = 0):
        self.plan = plan
        self.active_task_id = active_task_id
        self.proc_remaining = proc_remaining
        self.proc_overrun = proc_overrun
        self.coin_balance = coin_balance
        self.coin_streak = coin_streak
        self._refresh_display()
