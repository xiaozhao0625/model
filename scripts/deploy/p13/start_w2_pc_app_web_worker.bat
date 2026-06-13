@echo off
REM P13 W2 PC App/Web Worker startup template.
REM Copy configs\deploy\w2_pc_app_web_worker.production.env.example to .env on W2 first.
set PROJECT_ROOT=%~dp0..\..\..
set WORKER_CONFIG=%PROJECT_ROOT%\configs\workers\worker_agent.single_node_dev.example.json
cd /d "%PROJECT_ROOT%"
echo Starting W2 worker via Master API boundary. No database connection is used.
echo Edit WORKER_CONFIG to point at the W2 production worker config before real deployment.
python scripts\dev\run_worker_once_http.py --config "%WORKER_CONFIG%" --worker-id worker_web_stub_single_node
