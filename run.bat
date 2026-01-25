@echo off
TITLE Honda FBR Invoice Uploader
echo Starting application...

:: Check if venv exists
if not exist venv (
    echo Virtual environment not found. Running setup first...
    call setup.bat
)

:: Activate venv and run
call venv\Scripts\activate
python -m app.main

if %errorlevel% neq 0 (
    echo.
    echo Application crashed or closed with an error.
    pause
)
