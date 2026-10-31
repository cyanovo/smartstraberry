@echo off
setlocal

cd /d "%~dp0.."

echo Initializing with China-friendly mirrors...
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0init.ps1"

if errorlevel 1 (
  echo.
  echo Initialization failed. Please make sure Docker Desktop is running and try again.
  exit /b %errorlevel%
)

echo.
echo Initialization complete. You can now run:
echo docker compose up -d --build
