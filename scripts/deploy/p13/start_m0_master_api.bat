@echo off
REM P13 M0 Master API startup template.
REM Edit PROJECT_ROOT and ensure .env exists on M0. Do not commit .env.
set PROJECT_ROOT=%~dp0..\..\..
cd /d "%PROJECT_ROOT%"
echo Starting Master API. DATABASE_URL will not be printed.
python scripts\dev\run_master_http_dev.py
