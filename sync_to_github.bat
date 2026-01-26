@echo off
echo ==========================================
echo      FBR Invoice Uploader - Auto Sync
echo ==========================================
echo.

echo 1. Downloading latest changes (Git Pull)...
git pull origin main -X ours
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Pull failed! You might have conflicts.
    echo Please resolve conflicts manually.
    pause
    exit /b
)

echo.
echo 2. Adding all local changes...
git add .

echo.
echo 3. Committing changes...
:: If there are no changes, git commit will exit with non-zero, but we continue to push anyway to be safe
git commit -m "Auto-sync: %date% %time%"

:: The post-commit hook at .git/hooks/post-commit might have triggered a push already
:: but we run it again to ensure synchronization even if commit was empty.

echo.
echo 4. Pushing to remote repository...
git push origin main

echo.
echo ==========================================
echo           Sync Complete!
echo ==========================================
echo.
pause
