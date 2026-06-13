@echo off
REM P13 W3 Android Worker startup template.
REM Copy configs\deploy\w3_android_worker.production.env.example to .env on W3 first.
set PROJECT_ROOT=%~dp0..\..\..
set WORKER_CONFIG=%PROJECT_ROOT%\configs\workers\worker_agent.single_node_dev.example.json
cd /d "%PROJECT_ROOT%"
echo Starting W3 worker via Master API boundary. No database connection is used.
echo Edit WORKER_CONFIG to point at the W3 production worker config before real deployment.
python scripts\dev\run_worker_once_http.py --config "%WORKER_CONFIG%" --worker-id worker_android_stub_single_node
