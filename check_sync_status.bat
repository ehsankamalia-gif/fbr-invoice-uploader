@echo off
title Check Sync Status
echo Checking status of Auto-Sync Service...
echo.

:: Check if the window with specific title exists
tasklist /v /fi "WINDOWTITLE eq FBR Invoice Uploader - Auto Sync Service" | find "FBR Invoice Uploader" >nul

if %ERRORLEVEL% == 0 (
    color 20
    echo [OK] The Auto-Sync Service is RUNNING.
    echo.
    echo You should see a window named "FBR Invoice Uploader - Auto Sync Service" in your taskbar.
) else (
    color 40
    echo [ALERT] The Auto-Sync Service is NOT RUNNING!
    echo.
    echo Please double-click 'start_auto_sync.bat' to start it.
)

echo.
pause
