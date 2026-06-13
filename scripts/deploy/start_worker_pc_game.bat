@echo off
REM Example template only. Edit MASTER_URL and WORKER_ID before use.
set MASTER_URL=http://127.0.0.1:8000
set WORKER_ID=w1_pc_game
set WORKER_TYPE=pc_game
python scripts\dev\run_worker_once_http.py --worker-type pc_game
