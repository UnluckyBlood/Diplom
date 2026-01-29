@echo off
echo ========================================
echo    Arduino Monitoring System v2.0
echo    Python 3.14 Совместимость
echo ========================================
echo.

REM Проверка Python
python --version > nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python не найден!
    echo Установите Python 3.14 или выше
    pause
    exit /b 1
)

REM Проверка виртуального окружения
if not exist "venv" (
    echo Создание виртуального окружения...
    python -m venv venv
)

REM Активация виртуального окружения
call venv\Scripts\activate.bat

REM Установка зависимостей
if not exist "requirements.txt" (
    echo [ERROR] Файл requirements.txt не найден!
    pause
    exit /b 1
)

echo Установка зависимостей...
pip install --upgrade pip
pip install -r requirements.txt

REM Запуск системы
echo.
echo ========================================
echo          ЗАПУСК СИСТЕМЫ
echo ========================================
echo.

python run.py

REM Если run.py не найден, запускаем компоненты по отдельности
if errorlevel 1 (
    echo Попытка запуска компонентов по отдельности...
    echo.
    
    echo [1] Запуск веб-сервера...
    start cmd /k "cd /d %~dp0 && python WebServer\webserver.py"
    
    timeout /t 3 /nobreak > nul
    
    echo [2] Запуск обработчика данных...
    start cmd /k "cd /d %~dp0 && python DataProcessor\main.py"
    
    echo.
    echo Система запущена!
    echo Веб-интерфейс: http://localhost:8000
    echo.
    pause
)

REM Деактивация виртуального окружения
deactivate