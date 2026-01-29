@echo off
chcp 1251 > nul
title Arduino Monitoring System
color 0A

echo ========================================
echo    Arduino Monitoring System v1.0
echo ========================================
echo.

echo [1] Checking Python...
python --version
if errorlevel 1 (
    echo ERROR: Python not found
    pause
    exit /b 1
)

echo [2] Creating virtual environment if needed...
if not exist "venv" (
    echo Creating venv...
    python -m venv venv
)

echo [3] Activating virtual environment...
call venv\Scripts\activate.bat

echo [4] Installing dependencies...
pip install fastapi uvicorn pyserial requests websockets --quiet

echo.
echo [5] Starting Web Server...
start "Web Server" cmd /k "cd /d %~dp0 && call venv\Scripts\activate.bat && python WebServer\webserver.py"

timeout /t 5 > nul

echo [6] Starting Data Processor...
start "Data Processor" cmd /k "cd /d %~dp0 && call venv\Scripts\activate.bat && python DataProcessor\simple_main.py"

echo.
echo ========================================
echo    SYSTEM STARTED!
echo ========================================
echo.
echo Open in browser: http://localhost:8000
echo.
echo To stop: Close both CMD windows
echo.
pause
