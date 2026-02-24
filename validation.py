"""Валидация плана дня — мягкие предупреждения."""
from datetime import datetime, date
from adapter import DayPlan, TaskStatus


def check_plan(plan: DayPlan) -> list[str]:
    """
    Возвращает список предупреждений (строки).
    Пустой список = всё ок.
    """
    warnings = []
    active_tasks = [t for t in plan.tasks
                    if t.status not in (TaskStatus.COMPLETED, TaskStatus.SKIPPED)]

    # 1. Суммарное время > 24ч
    total = sum(t.allocated_seconds for t in active_tasks)
    if total > 86400:
        h = total // 3600
        warnings.append(f"⚠ Суммарное время задач {h}ч — больше суток")

    # 2. Пересечения по scheduled_time
    timed = []
    for t in active_tasks:
        if not t.scheduled_time:
            continue
        try:
            start = datetime.strptime(
                f"{date.today().isoformat()} {t.scheduled_time}", "%Y-%m-%d %H:%M"
            )
            end_sec = start.timestamp() + t.allocated_seconds
            timed.append((t.name, start.timestamp(), end_sec))
        except ValueError:
            continue

    timed.sort(key=lambda x: x[1])
    for i in range(len(timed) - 1):
        a_name, a_start, a_end = timed[i]
        b_name, b_start, b_end = timed[i + 1]
        if b_start < a_end:
            overlap = int(a_end - b_start) // 60
            warnings.append(
                f"⚠ «{a_name}» и «{b_name}» пересекаются на {overlap} мин"
            )

    return warnings
