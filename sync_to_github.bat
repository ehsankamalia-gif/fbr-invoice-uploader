@echo off
setlocal enabledelayedexpansion

echo ==========================================
echo      Auto-Syncing Changes to GitHub
echo ==========================================
echo.

for /f "tokens=*" %%b in ('git branch --show-current') do set CUR_BRANCH=%%b
if /i not "!CUR_BRANCH!"=="master" (
  echo Current branch is "!CUR_BRANCH!". Please switch to "master".
  echo Aborting sync to avoid pushing to the wrong branch.
  pause
  exit /b 1
)

echo 1. Adding all changes...
git add .

echo 2. Committing changes...
git commit -m "Auto-update: %date% %time% - Sync on master"
if errorlevel 1 (
  echo No changes to commit or commit failed.
)

echo 3. Pulling latest from origin/master with rebase...
git pull --rebase origin master
if errorlevel 1 (
  echo Pull/rebase failed. Resolve conflicts and rerun.
  pause
  exit /b 1
)

echo 4. Pushing to remote repository (origin/master)...
git push origin master

echo.
echo ==========================================
echo           Sync Complete!
echo ==========================================
echo.
pause
