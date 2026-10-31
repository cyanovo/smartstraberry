@echo off
set "PATH=%~dp0runtimes\node;%PATH%"
set "COREPACK_ENABLE_PROJECT_SPEC=0"
set "npm_config_manage_package_manager_versions=false"
cd /d "%~dp0Newsmart-Strawberry\web"
call pnpm dev
pause
