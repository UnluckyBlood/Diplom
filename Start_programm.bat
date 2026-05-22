@echo off
cd /d "%~dp0"

:: Запуск Ollama в фоне
start "Ollama" ollama serve

:: DataProcessor (если ему нужны библиотеки из venv – аналогично)
start "DataProcessor" openwebui-venv\Scripts\python.exe DataProcessor\main.py

:: WebServer – используем python из venv напрямую
start "WebServer" openwebui-venv\Scripts\python.exe WebServer\webserver.py

timeout /t 5 >nul
start http://localhost:8000
exit