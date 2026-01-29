@echo off
title Arduino Monitoring System
color 0A
echo =======================================================
echo               ARDUINO MONITORING SYSTEM
echo =======================================================
echo.
echo Подготовка системы...

REM Проверка виртуального окружения
if not exist "venv\Scripts\activate.bat" (
    echo Создание виртуального окружения...
    python -m venv venv
)

REM Активация виртуального окружения
call venv\Scripts\activate.bat

REM Установка зависимостей
echo Установка зависимостей...
pip install fastapi uvicorn pyserial requests websockets --quiet

echo.
echo =======================================================
echo               ЗАПУСК КОМПОНЕНТОВ
echo =======================================================
echo.

REM Запуск веб-сервера
echo [1] Запуск веб-сервера...
start "Web Server" cmd /k "cd /d %~dp0 && call venv\Scripts\activate.bat && python WebServer\webserver.py"

timeout /t 5 /nobreak > nul

REM Запуск обработчика данных
echo [2] Запуск обработчика данных...
start "Data Processor" cmd /k "cd /d %~dp0 && call venv\Scripts\activate.bat && python DataProcessor\simple_main.py"

echo.
echo =======================================================
echo             СИСТЕМА УСПЕШНО ЗАПУЩЕНА!
echo =======================================================
echo.
echo ?? ДОСТУПНЫЕ АДРЕСА:
echo    ?? Веб-интерфейс: http://localhost:8000
echo    ? WebSocket: ws://localhost:8000/ws
echo    ?? API данные: POST http://localhost:8000/api/data
echo    ?? API статус: GET http://localhost:8000/api/status
echo    ?? API текущие: GET http://localhost:8000/api/current
echo.
echo ?? КОНФИГУРАЦИЯ:
echo    Порт Arduino: COM3
echo    База данных: sensor_data.db
echo    AI модуль: simple_ai.py
echo.
echo ??  УПРАВЛЕНИЕ:
echo    • Для остановки закройте оба окна командной строки
echo    • Первое окно - Веб-сервер
echo    • Второе окно - Обработчик данных
echo.
echo =======================================================
echo Нажмите любую клавишу для выхода из запускатора...
pause > nul
