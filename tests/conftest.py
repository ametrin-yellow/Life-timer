import sys, os

# Добавляем корень проекта в sys.path.
# Работает независимо от того, откуда запущен pytest.
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)
