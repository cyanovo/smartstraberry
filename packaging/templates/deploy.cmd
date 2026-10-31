@echo off
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0deploy.ps1"
if errorlevel 1 echo Deployment failed. Give the console error and AGENT_DEPLOY.md to your agent.
pause
