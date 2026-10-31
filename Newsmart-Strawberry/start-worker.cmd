@echo off
"%~dp0backend\.venv\Scripts\python.exe" "%~dp0backend\run_local.py" --worker
if errorlevel 1 pause
