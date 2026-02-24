#!/bin/bash
set -e

echo "╔══════════════════════════════════════╗"
echo "║    Life Timer — сборка (macOS/Linux) ║"
echo "╚══════════════════════════════════════╝"
echo

# Проверяем Python
if ! command -v python3 &>/dev/null; then
    echo "[ОШИБКА] Python3 не найден. Установи Python 3.10+"
    exit 1
fi

echo "[1/3] Проверка зависимостей..."
pip3 install -r requirements.txt --quiet
pip3 install pyinstaller --quiet

echo "[2/3] Очистка предыдущей сборки..."
rm -rf "dist/Life Timer" build

echo "[3/3] Сборка..."
if [[ "$OSTYPE" == "darwin"* ]]; then
    pyinstaller life_timer_mac.spec --noconfirm
    echo
    echo "══════════════════════════════════════"
    echo " Готово!"
    echo " Приложение: dist/Life Timer.app"
    echo " Для дистрибуции: zip -r Life-Timer-macos.zip dist/Life\\ Timer"
    echo "══════════════════════════════════════"
else
    # Linux — собираем как onedir без .app
    pyinstaller life_timer.spec --noconfirm
    echo
    echo "══════════════════════════════════════"
    echo " Готово! Папка: dist/Life Timer/"
    echo "══════════════════════════════════════"
fi
