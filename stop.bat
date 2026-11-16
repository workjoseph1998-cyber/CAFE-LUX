@echo off
setlocal
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\stop.ps1"
set "CAFE_LUX_EXIT=%errorlevel%"
if not "%CAFE_LUX_EXIT%"=="0" echo [Cafe LUX] stop failed. Read the error above. See docs\TROUBLESHOOTING.md.
exit /b %CAFE_LUX_EXIT%
