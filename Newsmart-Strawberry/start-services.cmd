@echo off
setlocal
title Strawberry Local Services Launcher
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\windows\services.ps1" start
set "RESULT=%ERRORLEVEL%"
echo.
if not "%RESULT%"=="0" (
    echo Startup failed. Please check the error messages above.
    pause
)
exit /b %RESULT%
