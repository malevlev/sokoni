@echo off
title Sokoni Watch — Hawker Stock Monitor
color 1F
echo.
echo  ╔══════════════════════════════════════════════╗
echo  ║        SOKONI WATCH v2.0                     ║
echo  ║   Nairobi Hawker Intelligence System         ║
echo  ╚══════════════════════════════════════════════╝
echo.
echo  [*] Checking Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo  [ERROR] Python not found! Download from python.org
    pause & exit /b 1
)
echo  [*] Installing Flask...
pip install -r requirements.txt -q
echo  [*] Setting up data...
if not exist "data" mkdir data
echo.
echo  ╔══════════════════════════════════════════════╗
echo  ║  SOKONI WATCH is LIVE!                       ║
echo  ║  Open: http://localhost:5000                 ║
echo  ║                                              ║
echo  ║  Admin:   admin / sokoni2024                 ║
echo  ║  Hawker:  mama_njeri / njeri2024             ║
echo  ╚══════════════════════════════════════════════╝
echo.
start http://localhost:5000
python app.py
pause
