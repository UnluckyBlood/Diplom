@echo off
cd /d "%~dp0"
:: »спользуем -w 0 дл€ указани€ последнего активного окна
wt -w 0 ollama serve ; python DataProcessor\main.py ; python WebServer\webserver.py
timeout /t 5 >nul
start http://localhost:8000
exit