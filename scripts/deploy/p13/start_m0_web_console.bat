@echo off
REM P13 M0 Web Console startup template.
set PROJECT_ROOT=%~dp0..\..\..
cd /d "%PROJECT_ROOT%\apps\web-console"
echo Starting Web Console. Configure VITE_MASTER_API_URL locally if needed.
npm run dev -- --host 0.0.0.0
