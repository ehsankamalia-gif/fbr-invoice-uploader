@echo off
echo ==========================================
echo      Auto-Syncing Changes to GitHub
echo ==========================================
echo.

echo 1. Adding all changes...
git add .

echo 2. Committing changes...
git commit -m "Auto-update: %date% %time% - Updates to UI, UpdateService, and Build System"

echo 3. Pushing to remote repository...
git push origin master

echo.
echo ==========================================
echo           Sync Complete!
echo ==========================================
echo.
pause
