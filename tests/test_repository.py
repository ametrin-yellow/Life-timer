"""
Тесты репозитория на in-memory SQLite.
Требуют SQLAlchemy — запускать локально: pip install sqlalchemy
"""
# sys.path правится ПЕРВЫМ — до любых других импортов.
# Иначе pytest может подхватить встроенный модуль 'database' из stdlib.
import sys, os
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)

import unittest
from datetime import date, timedelta
from sqlalchemy import create_engine

# Подменяем движок на in-memory ДО первого импорта database/repository
import lt_db as _db_module
_db_module.engine = create_engine("sqlite:///:memory:", echo=False)

import repository as repo
import lt_db as database
from lt_db import (
    init_db, TaskStatus, RewardType,
    Settings, CoinBalance, Template, Preset
)


class BaseRepoTest(unittest.TestCase):
    def setUp(self):
        database.Base.metadata.drop_all(database.engine)
        init_db()

    def _today(self):
        return date.today()


# ──────────────────────────────────────────────────────────
#  Settings
# ──────────────────────────────────────────────────────────

class TestSettings(BaseRepoTest):

    def test_default_settings_exist(self):
        s = repo.get_settings()
        self.assertIsNotNone(s)
        self.assertEqual(s.notify_before_minutes, 5)

    def test_save_settings(self):
        repo.save_settings({"notify_before_minutes": 15})
        s = repo.get_settings()
        self.assertEqual(s.notify_before_minutes, 15)


# ──────────────────────────────────────────────────────────
#  DayPlan
# ──────────────────────────────────────────────────────────

class TestDayPlan(BaseRepoTest):

    def test_create_plan(self):
        plan = repo.get_or_create_plan(self._today())
        self.assertIsNotNone(plan)
        self.assertEqual(plan.date, self._today())

    def test_get_or_create_idempotent(self):
        p1 = repo.get_or_create_plan(self._today())
        p2 = repo.get_or_create_plan(self._today())
        self.assertEqual(p1.id, p2.id)

    def test_update_plan(self):
        plan = repo.get_or_create_plan(self._today())
        repo.update_plan(plan.id, procrastination_used=300)
        plan2 = repo.get_or_create_plan(self._today())
        self.assertEqual(plan2.procrastination_used, 300)


# ──────────────────────────────────────────────────────────
#  Tasks
# ──────────────────────────────────────────────────────────

class TestTasks(BaseRepoTest):

    def _make_plan_and_task(self, name="Тест", alloc=3600):
        import uuid
        plan = repo.get_or_create_plan(self._today())
        task_id = str(uuid.uuid4())
        task = repo.add_task(plan.id, task_id, name, alloc)
        return plan, task

    def test_add_task_uses_task_id_not_plan_id(self):
        import uuid
        plan = repo.get_or_create_plan(self._today())
        task_id = str(uuid.uuid4())
        task = repo.add_task(plan.id, task_id, "Задача", 1800)
        # Критический баг который мы уже исправили: id должен быть task_id
        self.assertEqual(task.id, task_id)
        self.assertNotEqual(task.id, str(plan.id))

    def test_add_multiple_tasks_unique_ids(self):
        import uuid
        plan = repo.get_or_create_plan(self._today())
        ids = [str(uuid.uuid4()) for _ in range(3)]
        for i, tid in enumerate(ids):
            repo.add_task(plan.id, tid, f"Задача {i}", 1800)
        tasks = repo.get_tasks_for_plan(plan.id)
        self.assertEqual(len(tasks), 3)
        task_ids = {t.id for t in tasks}
        self.assertEqual(task_ids, set(ids))

    def test_update_task_status(self):
        _, task = self._make_plan_and_task()
        repo.update_task(task.id, status=TaskStatus.COMPLETED)
        plan = repo.get_plan_with_tasks(self._today())
        t = next(t for t in plan.tasks if t.id == task.id)
        self.assertEqual(t.status, TaskStatus.COMPLETED)

    def test_delete_task(self):
        plan, task = self._make_plan_and_task()
        repo.delete_task(task.id)
        tasks = repo.get_tasks_for_plan(plan.id)
        self.assertEqual(len(tasks), 0)

    def test_get_unfinished(self):
        import uuid
        plan = repo.get_or_create_plan(self._today())
        # Добавляем 3 задачи: 1 pending, 1 completed, 1 skipped
        t1 = repo.add_task(plan.id, str(uuid.uuid4()), "Активная", 1800)
        t2 = repo.add_task(plan.id, str(uuid.uuid4()), "Выполнена", 1800)
        t3 = repo.add_task(plan.id, str(uuid.uuid4()), "Пропущена", 1800)
        repo.update_task(t2.id, status=TaskStatus.COMPLETED)
        repo.update_task(t3.id, status=TaskStatus.SKIPPED)
        unfinished = repo.get_unfinished_from_date(self._today())
        self.assertEqual(len(unfinished), 1)
        self.assertEqual(unfinished[0].id, t1.id)


# ──────────────────────────────────────────────────────────
#  Геймификация — баланс и транзакции
# ──────────────────────────────────────────────────────────

class TestBalance(BaseRepoTest):

    def test_initial_balance_zero(self):
        bal = repo.get_balance()
        self.assertEqual(bal.balance, 0)

    def test_add_positive_transaction(self):
        new_bal = repo.add_transaction(50, "Бонус")
        self.assertEqual(new_bal, 50)
        self.assertEqual(repo.get_balance().balance, 50)

    def test_add_negative_transaction(self):
        repo.add_transaction(100, "Бонус")
        new_bal = repo.add_transaction(-30, "Штраф")
        self.assertEqual(new_bal, 70)

    def test_negative_blocked_when_not_allowed(self):
        # allow_negative_balance=False (по умолчанию) — не уходим в минус
        repo.add_transaction(20, "Бонус")
        new_bal = repo.add_transaction(-50, "Штраф")
        self.assertGreaterEqual(new_bal, 0)

    def test_streak_update(self):
        repo.update_streak(5)
        self.assertEqual(repo.get_balance().streak, 5)

    def test_transactions_history(self):
        repo.add_transaction(10, "Бонус 1")
        repo.add_transaction(20, "Бонус 2")
        txs = repo.get_transactions()
        self.assertEqual(len(txs), 2)


# ──────────────────────────────────────────────────────────
#  Магазин
# ──────────────────────────────────────────────────────────

class TestRewards(BaseRepoTest):

    def test_add_and_get_reward(self):
        repo.add_reward("Кофе", 50, RewardType.SINGLE)
        rewards = repo.get_rewards()
        self.assertEqual(len(rewards), 1)
        self.assertEqual(rewards[0].name, "Кофе")

    def test_purchase_reward(self):
        repo.add_transaction(100, "Стартовый бонус")
        r = repo.add_reward("Кофе", 50, RewardType.SINGLE)
        new_bal = repo.purchase_reward(r.id)
        self.assertEqual(new_bal, 50)

    def test_purchase_insufficient_funds(self):
        r = repo.add_reward("Дорогое", 999, RewardType.SINGLE)
        with self.assertRaises(ValueError):
            repo.purchase_reward(r.id)

    def test_limited_reward_decrements_count(self):
        repo.add_transaction(200, "Бонус")
        r = repo.add_reward("Лимитка", 10, RewardType.LIMITED, count=3)
        repo.purchase_reward(r.id)
        rewards = repo.get_rewards()
        self.assertEqual(rewards[0].count, 2)

    def test_limited_reward_sold_out(self):
        repo.add_transaction(200, "Бонус")
        r = repo.add_reward("Последний", 10, RewardType.LIMITED, count=1)
        repo.purchase_reward(r.id)
        with self.assertRaises(ValueError):
            repo.purchase_reward(r.id)

    def test_delete_reward(self):
        r = repo.add_reward("Удаляемое", 10, RewardType.SINGLE)
        repo.delete_reward(r.id)
        self.assertEqual(len(repo.get_rewards()), 0)


# ──────────────────────────────────────────────────────────
#  Статистика
# ──────────────────────────────────────────────────────────

class TestStats(BaseRepoTest):

    def _seed_day(self, d: date, completed: int, skipped: int):
        import uuid
        plan = repo.get_or_create_plan(d)
        for i in range(completed):
            tid = str(uuid.uuid4())
            repo.add_task(plan.id, tid, f"Выполнено {i}", 3600)
            repo.update_task(tid, status=TaskStatus.COMPLETED,
                             elapsed_seconds=3600)
        for i in range(skipped):
            tid = str(uuid.uuid4())
            repo.add_task(plan.id, tid, f"Пропущено {i}", 1800)
            repo.update_task(tid, status=TaskStatus.SKIPPED)

    def test_empty_stats(self):
        summary = repo.get_stats_summary()
        self.assertEqual(summary["total_tasks"], 0)

    def test_stats_today(self):
        self._seed_day(date.today(), completed=3, skipped=1)
        summary = repo.get_stats_summary(
            date_from=date.today(), date_to=date.today()
        )
        self.assertEqual(summary["total_tasks"], 4)
        self.assertEqual(summary["completed_tasks"], 3)
        self.assertEqual(summary["skipped_tasks"], 1)
        self.assertEqual(summary["completion_rate"], 75)

    def test_stats_date_range(self):
        today = date.today()
        yesterday = today - timedelta(days=1)
        self._seed_day(today,     completed=2, skipped=0)
        self._seed_day(yesterday, completed=1, skipped=1)
        summary = repo.get_stats_summary(date_from=yesterday, date_to=today)
        self.assertEqual(summary["total_tasks"], 4)
        self.assertEqual(summary["completed_tasks"], 3)

    def test_stats_all_time(self):
        self._seed_day(date.today(),                      completed=2, skipped=0)
        self._seed_day(date.today() - timedelta(days=10), completed=1, skipped=1)
        summary = repo.get_stats_summary(date_from=None, date_to=date.today())
        self.assertEqual(summary["total_tasks"], 4)


# ──────────────────────────────────────────────────────────
#  Шаблоны и пресеты
# ──────────────────────────────────────────────────────────

class TestTemplates(BaseRepoTest):

    def test_builtin_templates_seeded(self):
        templates = repo.get_templates()
        builtins = [t for t in templates if t.is_builtin]
        self.assertGreater(len(builtins), 0)

    def test_add_user_template(self):
        repo.add_user_template("Йога", 2700, "🏃 Активность")
        templates = repo.get_templates()
        user = [t for t in templates if not t.is_builtin]
        self.assertEqual(len(user), 1)
        self.assertEqual(user[0].name, "Йога")

    def test_delete_user_template(self):
        t = repo.add_user_template("Удаляемый", 1800, "👤 Мои шаблоны")
        repo.delete_user_template(t.id)
        user = [t for t in repo.get_templates() if not t.is_builtin]
        self.assertEqual(len(user), 0)

    def test_cannot_delete_builtin_template(self):
        builtins = [t for t in repo.get_templates() if t.is_builtin]
        builtin_id = builtins[0].id
        repo.delete_user_template(builtin_id)  # должна быть no-op
        # Встроенный шаблон остался
        still_there = [t for t in repo.get_templates() if t.id == builtin_id]
        self.assertEqual(len(still_there), 1)

    def test_builtin_presets_seeded(self):
        presets = repo.get_presets()
        builtins = [p for p in presets if p.is_builtin]
        self.assertGreater(len(builtins), 0)

    def test_add_and_delete_user_preset(self):
        templates = [t for t in repo.get_templates() if t.is_builtin]
        ids = [templates[0].id, templates[1].id]
        p = repo.add_user_preset("Мой пресет", ids)
        self.assertIsNotNone(p.id)
        repo.delete_user_preset(p.id)
        user_presets = [p for p in repo.get_presets() if not p.is_builtin]
        self.assertEqual(len(user_presets), 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
