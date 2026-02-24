"""
Тесты валидации плана дня.
Не требуют БД.
"""
import sys, os
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)

import unittest
from unittest.mock import MagicMock
import enum

# Свой TaskStatus
class TaskStatus(str, enum.Enum):
    PENDING   = "pending"
    ACTIVE    = "active"
    COMPLETED = "completed"
    SKIPPED   = "skipped"

# Мок database — должен содержать все нужные enum'ы ДО импорта adapter
import types

class OverrunBehavior(str, enum.Enum):
    CONTINUE = "continue"
    STOP     = "stop"

class OverrunSource(str, enum.Enum):
    PROCRASTINATION = "procrastination"
    PROPORTIONAL    = "proportional"

db_mock = types.ModuleType("database")
db_mock.TaskStatus      = TaskStatus
db_mock.OverrunBehavior = OverrunBehavior
db_mock.OverrunSource   = OverrunSource
sys.modules["lt_db"] = db_mock
sys.modules["repository"] = MagicMock()

import adapter
adapter.TaskStatus = TaskStatus

from adapter import Task, DayPlan
from validation import check_plan


def make_task(name, allocated_seconds, scheduled_time=None,
              status=TaskStatus.PENDING) -> Task:
    return Task(
        name=name,
        allocated_seconds=allocated_seconds,
        scheduled_time=scheduled_time,
        status=status,
    )


class TestCheckPlan(unittest.TestCase):

    def test_empty_plan_no_warnings(self):
        plan = DayPlan(tasks=[])
        self.assertEqual(check_plan(plan), [])

    def test_normal_plan_no_warnings(self):
        plan = DayPlan(tasks=[
            make_task("Сон", 8 * 3600),
            make_task("Работа", 8 * 3600),
        ])
        self.assertEqual(check_plan(plan), [])

    def test_over_24h_triggers_warning(self):
        plan = DayPlan(tasks=[
            make_task("Задача 1", 50000),
            make_task("Задача 2", 50000),
        ])
        warnings = check_plan(plan)
        self.assertTrue(any("больше суток" in w for w in warnings))

    def test_over_24h_ignored_for_completed(self):
        # Завершённые задачи не считаются в сумму
        plan = DayPlan(tasks=[
            make_task("Завершено", 50000, status=TaskStatus.COMPLETED),
            make_task("Завершено 2", 50000, status=TaskStatus.COMPLETED),
        ])
        warnings = check_plan(plan)
        self.assertFalse(any("больше суток" in w for w in warnings))

    def test_no_overlap_no_warning(self):
        plan = DayPlan(tasks=[
            make_task("Завтрак",  1800, "08:00"),   # 08:00–08:30
            make_task("Работа",   3600, "09:00"),   # 09:00–10:00
        ])
        self.assertEqual(check_plan(plan), [])

    def test_overlap_triggers_warning(self):
        plan = DayPlan(tasks=[
            make_task("Встреча А", 3600, "09:00"),  # 09:00–10:00
            make_task("Встреча Б", 3600, "09:30"),  # 09:30–10:30 → пересечение 30 мин
        ])
        warnings = check_plan(plan)
        self.assertTrue(any("пересекаются" in w for w in warnings))

    def test_overlap_shows_correct_minutes(self):
        plan = DayPlan(tasks=[
            make_task("A", 3600, "10:00"),  # 10:00–11:00
            make_task("B", 3600, "10:15"),  # 10:15–11:15 → пересечение 45 мин
        ])
        warnings = check_plan(plan)
        self.assertTrue(any("45 мин" in w for w in warnings))

    def test_tasks_without_time_ignored_in_overlap(self):
        plan = DayPlan(tasks=[
            make_task("Без времени 1", 7200),
            make_task("Без времени 2", 7200),
        ])
        # Нет scheduled_time — пересечения не считаются
        warnings = check_plan(plan)
        self.assertFalse(any("пересекаются" in w for w in warnings))

    def test_skipped_task_excluded_from_overlap(self):
        plan = DayPlan(tasks=[
            make_task("Пропущено", 3600, "09:00", status=TaskStatus.SKIPPED),
            make_task("Активное",  3600, "09:00"),
        ])
        # Пропущенная задача не участвует в расчёте пересечений
        warnings = check_plan(plan)
        self.assertFalse(any("пересекаются" in w for w in warnings))


if __name__ == "__main__":
    unittest.main(verbosity=2)
