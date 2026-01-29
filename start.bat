@echo off
echo ========================================
echo    Arduino Monitoring System
echo ========================================
echo.

REM ��������� ������������ ���������
call venv\Scripts\activate.bat

echo [1] ������ ���-�������...
start cmd /k "cd /d %~dp0 && python WebServer\webserver.py"

timeout /t 3 /nobreak > nul

echo [2] ������ ����������� ������...
start cmd /k "cd /d %~dp0 && python DataProcessor\main.py"

echo.
echo ========================================
echo    ������� ��������
echo ========================================
echo.
echo ���-���������: http://localhost:8000
echo WebSocket: ws://localhost:8000/ws
echo.
echo ��� ��������� �������� ��� ���� ��������� ������
echo ========================================
pause
