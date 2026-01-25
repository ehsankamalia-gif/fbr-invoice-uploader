@echo off
setlocal enabledelayedexpansion
for /f "tokens=*" %%b in ('git branch --show-current') do set CUR_BRANCH=%%b
if /i not "!CUR_BRANCH!"=="master" (
    echo Current branch is "!CUR_BRANCH!". Please switch to "master" before building.
    pause
    exit /b 1
)

echo Building Honda FBR Uploader (Fast Launch Mode)...
echo This will create a folder 'dist\Honda_FBR_Uploader' containing the executable.
echo.
python build_exe.py
echo.
echo Copying configuration and database files to dist folder...
copy .env dist\Honda_FBR_Uploader\.env
copy fbr_invoices.db dist\Honda_FBR_Uploader\fbr_invoices.db
echo.
echo Build Complete!
echo ----------------------------------------------------------------
echo Your optimized application is located in:
echo    dist\Honda_FBR_Uploader\Honda_FBR_Uploader.exe
echo.
echo Note: For distribution, zip the entire 'Honda_FBR_Uploader' folder.
echo ----------------------------------------------------------------

