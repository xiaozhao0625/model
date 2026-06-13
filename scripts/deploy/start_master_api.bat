@echo off
REM Example template only. Edit MASTER_HOST, MASTER_PORT, and DATABASE_URL before use.
set MASTER_HOST=0.0.0.0
set MASTER_PORT=8000
python -m apps.master_api.main
