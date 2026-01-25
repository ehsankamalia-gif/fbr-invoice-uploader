@echo off
TITLE Honda FBR Invoice Uploader - Uninstall
echo Uninstalling Honda FBR Invoice Uploader...

if exist venv (
  call venv\Scripts\activate
)

python -c "import sys; from app.core.config import settings; from sqlalchemy.engine.url import make_url; from sqlalchemy import create_engine, text; \
u = make_url(settings.DB_URL); \
is_mysql = 'mysql' in settings.DB_URL; \
sys.stdout.write('Database URL: ' + settings.DB_URL + '\n'); \
\
import traceback; \
try:\
    if is_mysql:\
        server_url = u.set(database=''); \
        eng = create_engine(server_url); \
        with eng.connect() as conn:\
            conn.execute(text('DROP DATABASE IF EXISTS ' + u.database)); \
            conn.commit(); \
            sys.stdout.write('Dropped MySQL database: ' + u.database + '\n')\
except Exception as e:\
    sys.stdout.write('Skipping DB drop: ' + str(e) + '\n')"

python -c "from app.services.backup_service import backup_service; import shutil; import os; p = backup_service.app_data_dir; \
print('Removing app data dir:', p); \
shutil.rmtree(p, ignore_errors=True)"

if exist venv (
  echo Removing virtual environment...
  rmdir /S /Q venv
)

echo Uninstall complete.
pause
