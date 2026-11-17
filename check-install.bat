@echo off
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\check-install.ps1"
exit /b %errorlevel%
