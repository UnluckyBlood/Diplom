@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"

:: Проверяем Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ОШИБКА] Python не найден. Установите Python и добавьте в PATH.
    pause
    exit /b 1
)

:: Создаём venv, если нет
if not exist "openwebui-venv\Scripts\python.exe" (
    echo [INFO] Создание виртуального окружения...
    python -m venv openwebui-venv
)

:: Устанавливаем зависимости
if exist "requirements.txt" (
    echo [INFO] Установка зависимостей...
    openwebui-venv\Scripts\python.exe -m pip install -r requirements.txt --quiet
)

:: Абсолютные пути
set "VENV_PYTHON=%~dp0openwebui-venv\Scripts\python.exe"
set "DP_SCRIPT=%~dp0DataProcessor\main.py"
set "WS_SCRIPT=%~dp0WebServer\webserver.py"

:: Запуск в одном окне с тремя вкладками (wt понимает и относительные пути, но абсолютные надёжнее)
wt -w 0 nt --title "Ollama" ollama serve ; nt --title "DataProcessor" "%VENV_PYTHON%" "%DP_SCRIPT%" ; nt --title "WebServer" "%VENV_PYTHON%" "%WS_SCRIPT%"

:: Ждём запуска и открываем браузер
timeout /t 5 >nul
start http://localhost:8000
exit