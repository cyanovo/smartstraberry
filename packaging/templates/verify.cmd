@echo off
cd /d "%~dp0"
"Newsmart-Strawberry\backend\.venv\Scripts\python.exe" smoke_test.py
pause
