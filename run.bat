@echo off
title Payroll_View — Berlitz
color 1F
echo.
echo  ================================================
echo   Payroll_View v1.0
echo   Berlitz Payroll Management System
echo   SoftFlow Ltd (c) 2026
echo  ================================================
echo.
cd /d "%~dp0"

echo  [1/3] Checking dependencies...
pip install flask pandas openpyxl reportlab pypdf --quiet 2>nul
echo        Done.
echo.

echo  [2/3] Starting server, please wait...
start /B python app.py

echo  [3/3] Opening application...
timeout /t 4 /nobreak >nul

REM Try to open in Chrome app mode (no address bar)
set CHROME="C:\Program Files\Google\Chrome\Application\chrome.exe"
set EDGE="C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"

if exist %CHROME% (
    echo  Opening in Chrome...
    start "" %CHROME% --app=http://127.0.0.1:5001 --new-window --window-size=1280,900
) else if exist %EDGE% (
    echo  Opening in Edge...
    start "" %EDGE% --app=http://127.0.0.1:5001 --new-window --window-size=1280,900
) else (
    echo  Opening in default browser...
    start http://127.0.0.1:5001
)

echo.
echo  Payroll_View is running.
echo  Close the browser window and press any key to stop.
echo.
pause >nul
