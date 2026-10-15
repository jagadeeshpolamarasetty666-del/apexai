@echo off
title Apex AI Launcher
cd /d "C:\Users\jagad\apex-ai"

echo [1/3] Clearing stale ports...
powershell -Command "Get-NetTCPConnection -LocalPort 8000,5173 -State Listen -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique | Where-Object { $_ -gt 0 } | ForEach-Object { Stop-Process -Id $_ -Force }" >nul 2>&1

echo [2/3] Starting Apex Backend and UI Engines...
start /b python -m uvicorn server.main:app --host 127.0.0.1 --port 8000
cd ui
start /b npm run dev -- --host 127.0.0.1 --port 5173
cd ..

timeout /t 3 /nobreak >nul

echo [3/3] Launching Apex AI Desktop Shell...
start msedge --app="http://127.0.0.1:5173"
exit
