"""
Движок геймификации.
Работает только с доменными объектами, не знает про UI.

Формула стоимости задачи:
  coins = floor(allocated_minutes * PRIORITY_RATE)

  NORMAL  → 1 коин за 10 мин  (rate = 0.1)
  HIGH    → 1 коин за 5 мин   (rate = 0.2, т.е. ×2)
  LOW     → 0 коинов           (rate = 0.0, «без награды»)

Бонус за выполнение:
  - Вовремя или раньше: полная стоимость × (2 - elapsed/alloc)
  - С перерасходом до 2×: полная стоимость × (2 - alloc/elapsed)
  - Перерасход >2× → бонус 0, штраф

Штраф:
  - Скип / незакрытая / перерасход >2× → стоимость задачи (0 для LOW)
  - LOW задачи штрафов не дают
"""
from datetime import date
from typing import Optional
import math

from lt_db import Task, DayPlan, TaskStatus, Settings, Priority
import repository as repo


# ── Коэффициенты приоритета (коинов в секунду) ──
_PRIORITY_RATE: dict[str, float] = {
    Priority.HIGH.value:   1.0 / 300,   # 1 коин за 5 мин
    Priority.NORMAL.value: 1.0 / 600,   # 1 коин за 10 мин
    Priority.LOW.value:    0.0,          # без награды и штрафа
}


def _priority_value(task: Task) -> str:
    """Возвращает строковое значение приоритета (защита от None)."""
    if task.priority is None:
        return Priority.NORMAL.value
    return task.priority.value if hasattr(task.priority, "value") else str(task.priority)


def calc_task_base_coins(task: Task) -> int:
    """
    Базовая стоимость задачи в коинах.
    Зависит только от allocated_seconds и приоритета.
    Minimum 1 для HIGH/NORMAL, 0 для LOW.
    """
    rate = _PRIORITY_RATE.get(_priority_value(task), 1.0 / 600)
    base = task.allocated_seconds * rate
    if rate == 0.0:
        return 0
    return max(1, math.floor(base))


def calc_task_bonus(task: Task, base_bonus: int) -> int:
    """
    Рассчитывает бонус за завершённую задачу.

    LOW-задачи → 0.
    Остальные: base_coins × time_multiplier.
      Вовремя/раньше:  multiplier = 2 - elapsed/alloc  (от 2.0 до 1.0)
      Чуть позже <2×:  multiplier = 2 - alloc/elapsed  (от 1.0 до 0.5)
      >2×:             multiplier = 0
    """
    priority_str = _priority_value(task)
    if priority_str == Priority.LOW.value:
        return 0

    base_coins = calc_task_base_coins(task)
    alloc = task.allocated_seconds
    elapsed = task.elapsed_seconds

    if alloc <= 0:
        return base_coins

    ratio = elapsed / alloc

    if ratio <= 1.0:
        multiplier = 2.0 - ratio          # 2.0 → 1.0
    elif ratio <= 2.0:
        multiplier = 2.0 - (1.0 / ratio)  # 1.0 → 0.5
    else:
        return 0  # перерасход >2× — бонуса нет

    return max(1, math.floor(base_coins * multiplier))


def calc_task_penalty(task: Task, base_penalty: int, skip_count: int = 0) -> int:
    """
    Рассчитывает штраф.
    LOW-задачи → 0 (без награды = без наказания).
    Остальные → base_coins задачи при скипе/незакрытии/перерасходе >2×.
    """
    priority_str = _priority_value(task)
    if priority_str == Priority.LOW.value:
        return 0

    base_coins = calc_task_base_coins(task)

    if task.status == TaskStatus.SKIPPED:
        return base_coins

    if task.status == TaskStatus.COMPLETED:
        alloc = task.allocated_seconds
        elapsed = task.elapsed_seconds
        ratio = elapsed / alloc if alloc > 0 else 0
        if ratio > 2.0:
            return base_coins

    return 0


def calc_postpone_penalty(task: Task) -> int:
    """Штраф за перенос задачи на завтра = половина базовой стоимости."""
    priority_str = _priority_value(task)
    if priority_str == Priority.LOW.value:
        return 0
    return max(1, math.floor(calc_task_base_coins(task) * 0.5))


def calc_streak_multiplier(streak: int) -> float:
    """1 + 0.1 * min(N, 10)"""
    return 1.0 + 0.1 * min(streak, 10)


def calc_day_preview(plan_date: date) -> Optional[dict]:
    """
    Предварительный расчёт коинов за день (не записывает в БД).
    Возвращает словарь с прогнозом или None если геймификация выключена.

    Логика:
    - Завершённые задачи: считаем фактический бонус/штраф
    - Незавершённые: считаем потенциальный бонус (как будто выполнят вовремя)
    - Итог делим на потенциальный и уже заработанный
    """
    settings = repo.get_settings()
    if not settings.gamification_enabled:
        return None

    plan = repo.get_plan_with_tasks(plan_date)
    if not plan:
        return None

    balance = repo.get_balance()
    streak = balance.streak
    base_penalty = settings.base_penalty

    earned = 0       # уже заработано (завершённые задачи)
    potential = 0    # потенциально если выполнить оставшиеся вовремя
    penalties = 0    # уже начислено штрафов

    for task in plan.tasks:
        base = calc_task_base_coins(task)
        if task.status == TaskStatus.COMPLETED:
            earned += calc_task_bonus(task, base_penalty)
            penalties += calc_task_penalty(task, base_penalty)
        elif task.status == TaskStatus.SKIPPED:
            penalties += calc_task_penalty(task, base_penalty)
        else:
            # Незавершённая — потенциал: как будто выполнит ровно в allocated
            potential += base  # multiplier=1 при ratio=1

    multiplier = calc_streak_multiplier(streak)
    total_earned = int((earned - penalties) * multiplier)
    total_potential = int((earned + potential - penalties) * multiplier)

    return {
        "earned":       earned,
        "potential":    potential,
        "penalties":    penalties,
        "total_earned": total_earned,
        "total_potential": total_potential,
        "multiplier":   multiplier,
        "streak":       streak,
    }


def finalize_day(plan_date: date) -> Optional[dict]:
    """
    Подводит итог дня:
    - считает бонусы/штрафы по всем задачам
    - применяет стрик-множитель
    - начисляет коины
    - обновляет стрик
    Возвращает итоговый словарь или None если уже подведён.
    """
    settings = repo.get_settings()
    if not settings.gamification_enabled:
        return None

    plan = repo.get_plan_with_tasks(plan_date)
    if not plan or plan.day_finalized:
        return None

    balance = repo.get_balance()
    streak = balance.streak
    base_penalty = settings.base_penalty  # оставляем для обратной совместимости

    total_bonus = 0
    total_penalty = 0
    skip_count = 0

    for task in plan.tasks:
        if task.status == TaskStatus.COMPLETED:
            bonus = calc_task_bonus(task, base_penalty)
            penalty = calc_task_penalty(task, base_penalty)
            task.coins_earned = bonus
            task.coins_penalty = penalty
            total_bonus += bonus
            total_penalty += penalty

        elif task.status == TaskStatus.SKIPPED:
            skip_count += 1
            penalty = calc_task_penalty(task, base_penalty, skip_count)
            task.coins_penalty = penalty
            total_penalty += penalty

        elif task.status in (TaskStatus.PENDING, TaskStatus.ACTIVE):
            # Незакрытая задача = скип
            skip_count += 1
            penalty = calc_task_penalty(task, base_penalty)
            task.coins_penalty = penalty
            total_penalty += penalty

    # Стрик-множитель
    multiplier = calc_streak_multiplier(streak)
    raw_total = total_bonus - total_penalty
    day_total = math.floor(raw_total * multiplier)

    # Обновляем стрик
    if day_total < 0:
        new_streak = 0
    else:
        new_streak = streak + 1

    # Сохраняем итоги дня
    repo.update_plan(plan.id,
                     day_bonus=total_bonus,
                     day_penalty=total_penalty,
                     day_total=day_total,
                     day_finalized=True)

    # Начисляем коины
    if day_total != 0:
        repo.add_transaction(
            amount=day_total,
            reason=f"Итог дня {plan_date} (×{multiplier:.1f} стрик)",
            plan_date=plan_date,
        )

    repo.update_streak(new_streak)

    return {
        "bonus":         total_bonus,
        "penalty":       total_penalty,
        "multiplier":    multiplier,
        "total":         day_total,
        "streak":        new_streak,
        "streak_broken": new_streak == 0 and streak > 0,
    }
