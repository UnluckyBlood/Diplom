@echo off
cd /d "%~dp0"
powershell -ExecutionPolicy Bypass -File "%~dp0Install_Main_soft.ps1"
pause