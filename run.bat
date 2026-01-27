@echo off
setlocal enabledelayedexpansion
for /f "tokens=*" %%b in ('git branch --show-current') do set CUR_BRANCH=%%b
if /i not "!CUR_BRANCH!"=="main" (
    echo Current branch is "!CUR_BRANCH!". Please switch to "main" before running.
    pause
    exit /b 1
)

TITLE Honda FBR Invoice Uploader
echo Starting application...

:: Check if venv exists
if not exist venv (
    echo Virtual environment not found. Running setup first...
    call setup.bat
)

:: Activate venv and run
call venv\Scripts\activate
venv\Scripts\python -m app.main

if %errorlevel% neq 0 (
    echo.
    echo Application crashed or closed with an error.
    pause
)
