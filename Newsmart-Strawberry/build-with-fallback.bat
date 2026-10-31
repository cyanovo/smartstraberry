@echo off
setlocal
rem ============================================================
rem  build-with-fallback.bat - detect local mirror, then build.
rem  Double-click: docker compose up -d --build
rem    mirror reachable -> use local mirror
rem    mirror down      -> automatic public-internet fallback
rem  Usage: build-with-fallback.bat [mirror-ip]  (default 192.168.31.83)
rem ============================================================
set "SCRIPT_DIR=%~dp0"
set "MIRROR_HOST=%~1"
if "%MIRROR_HOST%"=="" set "MIRROR_HOST=192.168.31.83"
echo.
echo Detecting mirror %MIRROR_HOST% (local mirror; public fallback if down)...
echo.
powershell -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT_DIR%build-with-fallback.ps1" -ProjectRoot "%SCRIPT_DIR%" -MirrorHostIp "%MIRROR_HOST%" -Up
set "EXIT=%ERRORLEVEL%"
echo.
echo Build finished, exit code: %EXIT%
echo.
pause
exit /b %EXIT%
