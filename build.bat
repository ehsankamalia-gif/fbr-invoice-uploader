@echo off
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

