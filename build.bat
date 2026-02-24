@echo off
chcp 65001 >nul
echo ╔══════════════════════════════════════╗
echo ║       Life Timer — сборка exe        ║
echo ╚══════════════════════════════════════╝
echo.

:: Проверяем Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ОШИБКА] Python не найден. Установи Python 3.10+
    pause & exit /b 1
)

:: Устанавливаем зависимости если нужно
echo [1/3] Проверка зависимостей...
pip install -r requirements.txt --quiet
pip install pyinstaller --quiet

:: Чистим старую сборку
echo [2/3] Очистка предыдущей сборки...
if exist dist\life_timer rmdir /s /q dist\life_timer
if exist build rmdir /s /q build

:: Собираем
echo [3/3] Сборка...
pyinstaller life_timer.spec --noconfirm

if errorlevel 1 (
    echo.
    echo [ОШИБКА] Сборка провалилась. См. лог выше.
    pause & exit /b 1
)

:: Копируем БД шаблон если есть
if exist life_timer_default.db (
    copy life_timer_default.db "dist\Life Timer\" >nul
)

echo.
echo ══════════════════════════════════════
echo  Готово! Папка: dist\Life Timer\
echo  Запускай: dist\Life Timer\Life Timer.exe
echo ══════════════════════════════════════
echo.
echo Для релиза — заархивируй папку dist\Life Timer\
echo и выложи на GitHub Releases.
echo.
pause
