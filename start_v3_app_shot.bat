@echo off
setlocal
set SCRIPT_DIR=%~dp0
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT_DIR%start_v3_app_shot.ps1" %*
if errorlevel 1 (
  echo.
  echo V3 startup failed. See D:\work\app-shot\logs for details.
  pause
)
