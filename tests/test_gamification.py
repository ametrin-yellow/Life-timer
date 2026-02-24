"""
Тесты движка геймификации.
Не требуют БД — работают с чистыми объектами.

Формула:
  base_coins = floor(allocated_seconds / 600)   для NORMAL (1 коин за 10 мин)
  base_coins = floor(allocated_seconds / 300)   для HIGH   (1 коин за 5 мин)
  base_coins = 0                                для LOW    (без награды)
"""
import sys, os
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)

import unittest
from unittest.mock import MagicMock, patch
from datetime import date

# Мокаем database до импорта gamification — чтобы не нужна была БД
import types
import enum

# Настоящий TaskStatus
class TaskStatus(str, enum.Enum):
    PENDING   = "pending"
    ACTIVE    = "active"
    COMPLETED = "completed"
    SKIPPED   = "skipped"

# Настоящий Priority
class Priority(str, enum.Enum):
    HIGH   = "high"
    NORMAL = "normal"
    LOW    = "low"

db_mock = types.ModuleType("lt_db")
db_mock.Task       = MagicMock
db_mock.DayPlan    = MagicMock
db_mock.Settings   = MagicMock
db_mock.TaskStatus = TaskStatus
db_mock.Priority   = Priority
sys.modules["lt_db"]       = db_mock
sys.modules["repository"]  = MagicMock()

import gamification as gami


# ──────────────────────────────────────────────────────────
#  Вспомогалка
# ──────────────────────────────────────────────────────────

def make_task(allocated: int, elapsed: int,
              status=TaskStatus.COMPLETED,
              priority=Priority.NORMAL) -> MagicMock:
    t = MagicMock()
    t.allocated_seconds = allocated
    t.elapsed_seconds   = elapsed
    t.status            = status
    t.priority          = priority
    return t


# ──────────────────────────────────────────────────────────
#  calc_task_base_coins
# ──────────────────────────────────────────────────────────

class TestCalcTaskBaseCoins(unittest.TestCase):

    def test_normal_10min(self):
        # 10 мин → 1 коин
        t = make_task(600, 0, priority=Priority.NORMAL)
        self.assertEqual(gami.calc_task_base_coins(t), 1)

    def test_normal_60min(self):
        # 60 мин → 6 коинов
        t = make_task(3600, 0, priority=Priority.NORMAL)
        self.assertEqual(gami.calc_task_base_coins(t), 6)

    def test_high_5min(self):
        # HIGH 5 мин → 1 коин
        t = make_task(300, 0, priority=Priority.HIGH)
        self.assertEqual(gami.calc_task_base_coins(t), 1)

    def test_high_60min(self):
        # HIGH 60 мин → 12 коинов (×2 от NORMAL)
        t = make_task(3600, 0, priority=Priority.HIGH)
        self.assertEqual(gami.calc_task_base_coins(t), 12)

    def test_low_always_zero(self):
        # LOW → 0 коинов независимо от времени
        t = make_task(3600, 0, priority=Priority.LOW)
        self.assertEqual(gami.calc_task_base_coins(t), 0)

    def test_normal_minimum_is_one(self):
        # Меньше 10 мин NORMAL — всё равно минимум 1
        t = make_task(60, 0, priority=Priority.NORMAL)
        self.assertEqual(gami.calc_task_base_coins(t), 1)


# ──────────────────────────────────────────────────────────
#  calc_task_bonus
# ──────────────────────────────────────────────────────────

class TestCalcTaskBonus(unittest.TestCase):

    def test_low_always_zero_bonus(self):
        t = make_task(3600, 3600, priority=Priority.LOW)
        self.assertEqual(gami.calc_task_bonus(t, 10), 0)

    def test_normal_exact_on_time(self):
        # 60 мин NORMAL, выполнил точно → base=6, multiplier=1 → 6
        t = make_task(3600, 3600, priority=Priority.NORMAL)
        self.assertEqual(gami.calc_task_bonus(t, 10), 6)

    def test_normal_early_finish(self):
        # 60 мин, потратил 30 → ratio=0.5 → multiplier=1.5 → floor(6*1.5)=9
        t = make_task(3600, 1800, priority=Priority.NORMAL)
        self.assertEqual(gami.calc_task_bonus(t, 10), 9)

    def test_normal_zero_elapsed_max_bonus(self):
        # ratio=0 → multiplier=2 → 6*2=12
        t = make_task(3600, 0, priority=Priority.NORMAL)
        self.assertEqual(gami.calc_task_bonus(t, 10), 12)

    def test_high_double_vs_normal(self):
        # HIGH 60 мин на время → base=12, multiplier=1 → 12 (vs 6 для NORMAL)
        t = make_task(3600, 3600, priority=Priority.HIGH)
        self.assertEqual(gami.calc_task_bonus(t, 10), 12)

    def test_beyond_double_returns_zero(self):
        # elapsed > 2x → 0 независимо от приоритета
        t = make_task(3600, 7201, priority=Priority.NORMAL)
        self.assertEqual(gami.calc_task_bonus(t, 10), 0)

    def test_high_beyond_double_returns_zero(self):
        t = make_task(3600, 7201, priority=Priority.HIGH)
        self.assertEqual(gami.calc_task_bonus(t, 10), 0)

    def test_overrun_150pct_still_gives_bonus(self):
        # ratio=1.5 → multiplier = 2 - 1/1.5 ≈ 1.33 → floor(6*1.33)=7
        t = make_task(3600, 5400, priority=Priority.NORMAL)
        bonus = gami.calc_task_bonus(t, 10)
        self.assertGreater(bonus, 0)


# ──────────────────────────────────────────────────────────
#  calc_task_penalty
# ──────────────────────────────────────────────────────────

class TestCalcTaskPenalty(unittest.TestCase):

    def test_low_no_penalty_on_skip(self):
        # LOW задачи — нет штрафа даже за скип
        t = make_task(3600, 0, TaskStatus.SKIPPED, Priority.LOW)
        self.assertEqual(gami.calc_task_penalty(t, 10), 0)

    def test_normal_skip_penalty_equals_base_coins(self):
        # NORMAL 60 мин → base=6 → штраф за скип = 6
        t = make_task(3600, 0, TaskStatus.SKIPPED, Priority.NORMAL)
        self.assertEqual(gami.calc_task_penalty(t, 10), 6)

    def test_high_skip_penalty_equals_base_coins(self):
        # HIGH 60 мин → base=12 → штраф за скип = 12
        t = make_task(3600, 0, TaskStatus.SKIPPED, Priority.HIGH)
        self.assertEqual(gami.calc_task_penalty(t, 10), 12)

    def test_completed_on_time_no_penalty(self):
        t = make_task(3600, 3600, TaskStatus.COMPLETED, Priority.NORMAL)
        self.assertEqual(gami.calc_task_penalty(t, 10), 0)

    def test_completed_beyond_double_penalty(self):
        t = make_task(3600, 7201, TaskStatus.COMPLETED, Priority.NORMAL)
        self.assertEqual(gami.calc_task_penalty(t, 10), 6)

    def test_completed_exact_double_no_penalty(self):
        # ratio == 2.0 — граница, штрафа нет
        t = make_task(3600, 7200, TaskStatus.COMPLETED, Priority.NORMAL)
        self.assertEqual(gami.calc_task_penalty(t, 10), 0)


# ──────────────────────────────────────────────────────────
#  calc_postpone_penalty
# ──────────────────────────────────────────────────────────

class TestCalcPostponePenalty(unittest.TestCase):

    def test_low_no_postpone_penalty(self):
        t = make_task(3600, 0, priority=Priority.LOW)
        self.assertEqual(gami.calc_postpone_penalty(t), 0)

    def test_normal_postpone_half_base(self):
        # NORMAL 60 мин → base=6 → postpone = floor(6*0.5) = 3
        t = make_task(3600, 0, priority=Priority.NORMAL)
        self.assertEqual(gami.calc_postpone_penalty(t), 3)

    def test_high_postpone_half_base(self):
        # HIGH 60 мин → base=12 → postpone = floor(12*0.5) = 6
        t = make_task(3600, 0, priority=Priority.HIGH)
        self.assertEqual(gami.calc_postpone_penalty(t), 6)

    def test_minimum_is_one(self):
        t = make_task(120, 0, priority=Priority.NORMAL)  # 2 мин → base=1 → half=1
        self.assertGreaterEqual(gami.calc_postpone_penalty(t), 1)


# ──────────────────────────────────────────────────────────
#  calc_streak_multiplier
# ──────────────────────────────────────────────────────────

class TestCalcStreakMultiplier(unittest.TestCase):

    def test_zero_streak(self):
        self.assertAlmostEqual(gami.calc_streak_multiplier(0), 1.0)

    def test_one_streak(self):
        self.assertAlmostEqual(gami.calc_streak_multiplier(1), 1.1)

    def test_ten_streak(self):
        self.assertAlmostEqual(gami.calc_streak_multiplier(10), 2.0)

    def test_cap_at_ten(self):
        self.assertAlmostEqual(
            gami.calc_streak_multiplier(10),
            gami.calc_streak_multiplier(50),
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)

