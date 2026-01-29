@echo off
echo ========================================
echo    Arduino Monitoring System
echo ========================================
echo.

REM Активация виртуального окружения
call venv\Scripts\activate.bat

echo [1] Запуск веб-сервера...
start cmd /k "cd /d %~dp0 && python WebServer\webserver.py"

timeout /t 3 /nobreak > nul

echo [2] Запуск обработчика данных...
start cmd /k "cd /d %~dp0 && python DataProcessor\main.py"

echo.
echo ========================================
echo    СИСТЕМА ЗАПУЩЕНА
echo ========================================
echo.
echo Веб-интерфейс: http://localhost:8000
echo WebSocket: ws://localhost:8000/ws
echo.
echo Для остановки закройте оба окна командной строки
echo ========================================
pause
