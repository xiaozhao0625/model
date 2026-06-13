@echo off
REM Example template only. Edit MASTER_URL and WORKER_ID before use.
set MASTER_URL=http://127.0.0.1:8000
set WORKER_ID=w3_android
set WORKER_TYPE=android
python scripts\dev\run_worker_once_http.py --worker-type android
