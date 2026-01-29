@echo off
echo ========================================
echo    Arduino Monitoring System - FINAL
echo ========================================
echo.

REM Активация виртуального окружения
call venv\Scripts\activate.bat

echo [1] Установка зависимостей...
pip install requests > nul 2>&1

echo [2] Запуск веб-сервера...
start cmd /k "cd /d %~dp0 && python WebServer\webserver.py"

timeout /t 3 /nobreak > nul

echo [3] Запуск обработчика данных...
start cmd /k "cd /d %~dp0 && python DataProcessor\simple_main.py"

echo.
echo ========================================
echo         СИСТЕМА УСПЕШНО ЗАПУЩЕНА
echo ========================================
echo.
echo ?? Веб-интерфейс: http://localhost:8000
echo ?? Обработчик: COM3
echo ?? AI: Активен
echo ?? БД: sensor_data.db
echo.
echo Для остановки закройте оба окна командной строки
echo ========================================
echo.
pause
