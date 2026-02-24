"""
Магазин поощрений.
Две вкладки:
  🛍 Магазин  — список наград, кнопка «Купить»
  ✎ Управление — добавить / удалить награды
"""
import customtkinter as ctk
from tkinter import messagebox
from typing import Callable, Optional
import repository as repo
from lt_db import RewardType


TYPE_LABELS = {
    RewardType.LIMITED:      "лимитированное",
    RewardType.SUBSCRIPTION: "абонемент",
}
TYPE_COLORS = {
    RewardType.LIMITED:      "#7B1FA2",
    RewardType.SUBSCRIPTION: "#2E7D32",
}


class ShopDialog(ctk.CTkToplevel):

    def __init__(self, master, on_purchase: Optional[Callable] = None, **kwargs):
        super().__init__(master, **kwargs)
        self.title("🛍 Магазин")
        self.geometry("520x560")
        self.minsize(440, 400)
        self.resizable(True, True)
        self.on_purchase = on_purchase
        self.after(100, self._force_focus)
        self._build()

    def _force_focus(self):
        self.attributes("-topmost", True)
        self.lift()
        self.focus_force()
        self.after(200, lambda: self.attributes("-topmost", False))

    # ──────────────────────────────────────────────

    def _build(self):
        # Баланс вверху
        self._balance_frame = ctk.CTkFrame(self, fg_color="#1a1a2e", corner_radius=10)
        self._balance_frame.pack(fill="x", padx=14, pady=(12, 6))
        self._balance_lbl = ctk.CTkLabel(
            self._balance_frame, text="",
            font=("Helvetica", 20, "bold")
        )
        self._balance_lbl.pack(pady=8)
        self._refresh_balance()

        self.tabview = ctk.CTkTabview(self)
        self.tabview.pack(fill="both", expand=True, padx=14, pady=(0, 4))
        self.tabview.add("🛍 Магазин")
        self.tabview.add("✎ Управление")

        self._fill_shop(self.tabview.tab("🛍 Магазин"))
        self._fill_manage(self.tabview.tab("✎ Управление"))

        ctk.CTkButton(self, text="Закрыть", command=self.destroy,
                      width=100, fg_color="#444").pack(pady=8)

    # ──────────────────────────────────────────────
    #  Баланс
    # ──────────────────────────────────────────────

    def _refresh_balance(self):
        try:
            bal = repo.get_balance()
            color = "#4CAF50" if bal.balance >= 0 else "#EF5350"
            streak_txt = f"  🔥 {bal.streak} дн." if bal.streak > 0 else ""
            self._balance_lbl.configure(
                text=f"🪙 {bal.balance} коинов{streak_txt}",
                text_color=color
            )
        except Exception:
            self._balance_lbl.configure(text="🪙 —", text_color="gray")

    # ──────────────────────────────────────────────
    #  Вкладка Магазин
    # ──────────────────────────────────────────────

    def _fill_shop(self, parent):
        self._shop_frame = ctk.CTkScrollableFrame(parent, corner_radius=0,
                                                   fg_color="transparent")
        self._shop_frame.pack(fill="both", expand=True)
        self._render_shop()

    def _render_shop(self):
        for w in self._shop_frame.winfo_children():
            w.destroy()

        rewards = repo.get_rewards(active_only=True)
        if not rewards:
            ctk.CTkLabel(self._shop_frame,
                         text="Нет доступных наград.\nДобавь их во вкладке «Управление».",
                         text_color="gray", font=("Helvetica", 13),
                         justify="center").pack(expand=True, pady=30)
            return

        try:
            balance = repo.get_balance().balance
        except Exception:
            balance = 0

        for r in rewards:
            self._reward_card(self._shop_frame, r, balance)

    def _reward_card(self, parent, reward, balance: int):
        can_afford = balance >= reward.price
        is_sold_out = (reward.reward_type == RewardType.LIMITED
                       and reward.count is not None
                       and reward.count <= 0)

        card = ctk.CTkFrame(parent, corner_radius=8,
                             fg_color="#2a2a2a" if can_afford and not is_sold_out else "#1e1e1e")
        card.pack(fill="x", pady=3)

        # Левая часть — инфо
        info = ctk.CTkFrame(card, fg_color="transparent")
        info.pack(side="left", fill="both", expand=True, padx=10, pady=8)

        # Название + тип
        name_row = ctk.CTkFrame(info, fg_color="transparent")
        name_row.pack(anchor="w", fill="x")
        ctk.CTkLabel(name_row, text=reward.name,
                     font=("Helvetica", 13, "bold"),
                     text_color="white" if can_afford and not is_sold_out else "gray"
                     ).pack(side="left")

        type_color = TYPE_COLORS.get(reward.reward_type, "#888")
        type_label = TYPE_LABELS.get(reward.reward_type, "")
        from ui.tooltip import Tooltip, TIPS
        tip_key = ("reward_limited" if reward.reward_type == RewardType.LIMITED
                   else "reward_subscription")
        type_badge = ctk.CTkLabel(name_row, text=type_label,
                     font=("Helvetica", 10), text_color=type_color,
                     fg_color="#1a1a1a", corner_radius=4,
                     padx=4, pady=1)
        type_badge.pack(side="left", padx=(6, 0))
        Tooltip(type_badge, TIPS[tip_key])

        # Описание
        if reward.description:
            ctk.CTkLabel(info, text=reward.description,
                         font=("Helvetica", 11), text_color="#888",
                         anchor="w", wraplength=280).pack(anchor="w")

        # Остаток для лимитированных
        if reward.reward_type == RewardType.LIMITED and reward.count is not None:
            left_txt = f"Осталось: {reward.count}" if reward.count > 0 else "Закончилось"
            left_color = "#FFB74D" if reward.count > 0 else "#EF5350"
            ctk.CTkLabel(info, text=left_txt,
                         font=("Helvetica", 10), text_color=left_color).pack(anchor="w")

        # Правая часть — цена + кнопка
        right = ctk.CTkFrame(card, fg_color="transparent")
        right.pack(side="right", padx=10, pady=8)

        price_color = "#4CAF50" if can_afford else "#EF5350"
        ctk.CTkLabel(right, text=f"🪙 {reward.price}",
                     font=("Helvetica", 14, "bold"),
                     text_color=price_color).pack()

        if is_sold_out:
            ctk.CTkLabel(right, text="нет в наличии",
                         font=("Helvetica", 10), text_color="#555").pack()
        elif not can_afford:
            ctk.CTkLabel(right, text="не хватает",
                         font=("Helvetica", 10), text_color="#EF5350").pack()
        else:
            ctk.CTkButton(right, text="Купить", width=80, height=28,
                          fg_color="#1565C0", corner_radius=6,
                          command=lambda rid=reward.id: self._buy(rid)).pack()

    def _buy(self, reward_id: int):
        try:
            new_balance = repo.purchase_reward(reward_id)
            if self.on_purchase:
                self.on_purchase(new_balance)
            self._refresh_balance()
            self._render_shop()
        except ValueError as e:
            messagebox.showerror("Ошибка", str(e), parent=self)

    # ──────────────────────────────────────────────
    #  Вкладка Управление
    # ──────────────────────────────────────────────

    def _fill_manage(self, parent):
        # Форма добавления
        form = ctk.CTkFrame(parent, corner_radius=8)
        form.pack(fill="x", pady=(4, 8))

        ctk.CTkLabel(form, text="Добавить награду",
                     font=("Helvetica", 13, "bold")).pack(anchor="w", padx=10, pady=(8, 4))

        pad = {"padx": 10, "pady": 3}

        row1 = ctk.CTkFrame(form, fg_color="transparent")
        row1.pack(fill="x", **pad)
        ctk.CTkLabel(row1, text="Название:", width=90, anchor="w").pack(side="left")
        self._new_name = ctk.CTkEntry(row1, placeholder_text="Пицца / Эпизод сериала / ...")
        self._new_name.pack(side="left", fill="x", expand=True)

        row2 = ctk.CTkFrame(form, fg_color="transparent")
        row2.pack(fill="x", **pad)
        ctk.CTkLabel(row2, text="Цена (🪙):", width=90, anchor="w").pack(side="left")
        self._new_price = ctk.CTkEntry(row2, placeholder_text="50", width=80)
        self._new_price.pack(side="left", padx=(0, 10))

        ctk.CTkLabel(row2, text="Тип:", width=40, anchor="w").pack(side="left")
        self._new_type = ctk.CTkOptionMenu(
            row2,
            values=["лимитированное", "абонемент"],
            width=150,
            command=self._on_type_change,
        )
        self._new_type.pack(side="left")

        row3 = ctk.CTkFrame(form, fg_color="transparent")
        row3.pack(fill="x", **pad)
        ctk.CTkLabel(row3, text="Описание:", width=90, anchor="w").pack(side="left")
        self._new_desc = ctk.CTkEntry(row3, placeholder_text="опционально")
        self._new_desc.pack(side="left", fill="x", expand=True)

        # Кол-во для лимитированных
        row4 = ctk.CTkFrame(form, fg_color="transparent")
        row4.pack(fill="x", **pad)
        ctk.CTkLabel(row4, text="Кол-во:", width=90, anchor="w").pack(side="left")
        self._new_count = ctk.CTkEntry(row4, placeholder_text="для лимит. типа", width=120)
        self._new_count.pack(side="left")
        self._on_type_change(self._new_type.get())  # задаём начальное состояние

        ctk.CTkButton(form, text="+ Добавить награду", width=160,
                      fg_color="#1565C0", corner_radius=6,
                      command=self._add_reward).pack(anchor="e", padx=10, pady=(4, 10))

        # Список существующих
        ctk.CTkLabel(parent, text="Существующие награды:",
                     font=("Helvetica", 12, "bold"), anchor="w").pack(
                         fill="x", pady=(0, 2))

        self._manage_scroll = ctk.CTkScrollableFrame(parent, corner_radius=8)
        self._manage_scroll.pack(fill="both", expand=True)
        self._render_manage_list()

    def _render_manage_list(self):
        for w in self._manage_scroll.winfo_children():
            w.destroy()

        rewards = repo.get_rewards(active_only=False)
        if not rewards:
            ctk.CTkLabel(self._manage_scroll, text="Пока нет наград",
                         text_color="gray").pack(pady=10)
            return

        for r in rewards:
            self._reward_manage_row(self._manage_scroll, r)

    def _reward_manage_row(self, parent, r):
        """Строка с инлайн-редактированием награды."""
        container = ctk.CTkFrame(parent, fg_color="#222", corner_radius=6)
        container.pack(fill="x", pady=2)

        # ── Строка-превью ──
        preview = ctk.CTkFrame(container, fg_color="transparent")
        preview.pack(fill="x")

        type_str = TYPE_LABELS.get(r.reward_type, "")
        count_str = f" ({r.count} шт.)" if r.reward_type == RewardType.LIMITED and r.count is not None else ""
        label_text = f"{r.name}  —  🪙{r.price}  [{type_str}{count_str}]"
        ctk.CTkLabel(preview, text=label_text, font=("Helvetica", 12),
                     anchor="w").pack(side="left", padx=8, pady=6, fill="x", expand=True)

        btn_edit = ctk.CTkButton(preview, text="✎", width=30, height=26,
                                  fg_color="#1a3a5a", corner_radius=5)
        btn_edit.pack(side="right", padx=(2, 2))
        ctk.CTkButton(preview, text="✕", width=30, height=26,
                      fg_color="#4a1010", corner_radius=5,
                      command=lambda rid=r.id: self._delete_reward(rid)).pack(
                          side="right", padx=(2, 0))

        # ── Форма редактирования (скрыта) ──
        edit_frame = ctk.CTkFrame(container, fg_color="#1a1a1a", corner_radius=6)
        # не упакована — показываем по кнопке

        pad = {"padx": 8, "pady": 2}

        row1 = ctk.CTkFrame(edit_frame, fg_color="transparent")
        row1.pack(fill="x", **pad)
        ctk.CTkLabel(row1, text="Название:", width=80, anchor="w").pack(side="left")
        e_name = ctk.CTkEntry(row1)
        e_name.insert(0, r.name)
        e_name.pack(side="left", fill="x", expand=True)

        row2 = ctk.CTkFrame(edit_frame, fg_color="transparent")
        row2.pack(fill="x", **pad)
        ctk.CTkLabel(row2, text="Цена 🪙:", width=80, anchor="w").pack(side="left")
        e_price = ctk.CTkEntry(row2, width=80)
        e_price.insert(0, str(r.price))
        e_price.pack(side="left")

        row3 = ctk.CTkFrame(edit_frame, fg_color="transparent")
        row3.pack(fill="x", **pad)
        ctk.CTkLabel(row3, text="Описание:", width=80, anchor="w").pack(side="left")
        e_desc = ctk.CTkEntry(row3)
        e_desc.insert(0, r.description or "")
        e_desc.pack(side="left", fill="x", expand=True)

        # Пополнение остатка — только для лимитированных
        e_add = None
        if r.reward_type == RewardType.LIMITED:
            row4 = ctk.CTkFrame(edit_frame, fg_color="transparent")
            row4.pack(fill="x", **pad)
            ctk.CTkLabel(row4, text="+ добавить:", width=80, anchor="w").pack(side="left")
            e_add = ctk.CTkEntry(row4, width=80, placeholder_text="кол-во")
            e_add.pack(side="left")
            ctk.CTkLabel(row4, text=f"(сейчас: {r.count})", text_color="#888",
                         font=("Helvetica", 11)).pack(side="left", padx=6)

        btn_row = ctk.CTkFrame(edit_frame, fg_color="transparent")
        btn_row.pack(fill="x", padx=8, pady=(2, 8))

        def save():
            name = e_name.get().strip()
            if not name:
                messagebox.showerror("Ошибка", "Название не может быть пустым", parent=self)
                return
            try:
                price = int(e_price.get().strip())
                if price <= 0:
                    raise ValueError
            except ValueError:
                messagebox.showerror("Ошибка", "Цена — целое число > 0", parent=self)
                return
            count_add = 0
            if e_add is not None:
                val = e_add.get().strip()
                if val:
                    try:
                        count_add = int(val)
                        if count_add < 0:
                            raise ValueError
                    except ValueError:
                        messagebox.showerror("Ошибка", "Добавляемое кол-во — целое число ≥ 0", parent=self)
                        return
            desc = e_desc.get().strip() or None
            repo.update_reward(r.id, name=name, price=price,
                               description=desc, count_add=count_add)
            self._render_manage_list()
            self._render_shop()

        ctk.CTkButton(btn_row, text="Сохранить", width=100, height=26,
                      fg_color="#1B5E20", corner_radius=5,
                      command=save).pack(side="left", padx=(0, 6))
        ctk.CTkButton(btn_row, text="Отмена", width=80, height=26,
                      fg_color="#444", corner_radius=5,
                      command=lambda: _toggle(False)).pack(side="left")

        def _toggle(show: bool):
            if show:
                edit_frame.pack(fill="x", padx=4, pady=(0, 6))
                btn_edit.configure(fg_color="#2a5a2a")
            else:
                edit_frame.pack_forget()
                btn_edit.configure(fg_color="#1a3a5a")

        btn_edit.configure(command=lambda: _toggle(not edit_frame.winfo_ismapped()))

    def _on_type_change(self, value: str):
        """Блокируем поле кол-ва для абонемента."""
        is_limited = (value == "лимитированное")
        self._new_count.configure(state="normal" if is_limited else "disabled",
                                   placeholder_text="кол-во" if is_limited else "н/д")
        if not is_limited:
            self._new_count.delete(0, "end")

    def _add_reward(self):
        name = self._new_name.get().strip()
        if not name:
            messagebox.showerror("Ошибка", "Введи название награды", parent=self)
            return

        try:
            price = int(self._new_price.get().strip() or "0")
            if price <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Ошибка", "Цена должна быть целым числом > 0", parent=self)
            return

        type_map = {
            "лимитированное": RewardType.LIMITED,
            "абонемент":      RewardType.SUBSCRIPTION,
        }
        rtype = type_map[self._new_type.get()]

        count = None
        if rtype == RewardType.LIMITED:
            try:
                count = int(self._new_count.get().strip())
                if count <= 0:
                    raise ValueError
            except ValueError:
                messagebox.showerror("Ошибка",
                                     "Для лимитированного типа укажи кол-во (целое > 0)",
                                     parent=self)
                return

        desc = self._new_desc.get().strip() or None
        repo.add_reward(name=name, price=price, reward_type=rtype,
                        description=desc, count=count)

        self._new_name.delete(0, "end")
        self._new_price.delete(0, "end")
        self._new_desc.delete(0, "end")
        self._new_count.delete(0, "end")

        self._render_manage_list()
        self._render_shop()

    def _delete_reward(self, reward_id: int):
        if messagebox.askyesno("Удалить?", "Удалить эту награду?", parent=self):
            repo.delete_reward(reward_id)
            self._render_manage_list()
            self._render_shop()
