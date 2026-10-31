@echo off
set "PYTHONUTF8=1"
cd /d "%~dp0Newsmart-Strawberry\backend"
".venv\Scripts\python.exe" run_local.py
pause
