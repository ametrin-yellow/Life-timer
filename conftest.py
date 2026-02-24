# conftest.py — pytest подхватывает автоматически.
# Добавляет корень проекта в sys.path, чтобы импорты
# вида `import database`, `import repository` работали
# независимо от того, откуда запущен pytest.
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
