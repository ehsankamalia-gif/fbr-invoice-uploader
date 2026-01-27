import os
import shutil
import json
import time
import logging
import hashlib
import threading
import zipfile
import subprocess
import urllib.parse
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional
from app.core.config import settings

# Optional dependencies with graceful fallback
try:
    import schedule
except ImportError:
    schedule = None

try:
    from cryptography.fernet import Fernet
except ImportError:
    Fernet = None

try:
    import platformdirs
except ImportError:
    platformdirs = None

logger = logging.getLogger(__name__)

# Constants
APP_NAME = "fbr_invoice_uploader"
BACKUP_DIR_NAME = "backups"
CONFIG_FILE_NAME = "backup_config.json"

class BackupConfig:
    def __init__(self, 
                 enabled: bool = False,
                 interval: str = "daily",  # daily, weekly, monthly
                 time_str: str = "00:00",
                 local_path: str = "",
                 cloud_path: str = "",
                 retention_days: int = 30,
                 encrypt: bool = True,
                 encryption_key: str = ""):
        self.enabled = enabled
        self.interval = interval
        self.time_str = time_str
        self.local_path = local_path
        self.cloud_path = cloud_path
        self.retention_days = retention_days
        self.encrypt = encrypt
        self.encryption_key = encryption_key

    @classmethod
    def from_dict(cls, data: Dict):
        return cls(**data)

    def to_dict(self):
        return self.__dict__

class BackupService:
    def __init__(self):
        if platformdirs:
            self.app_data_dir = Path(platformdirs.user_data_dir(APP_NAME, appauthor=False))
        else:
            self.app_data_dir = Path.home() / f".{APP_NAME}"
            
        self.app_data_dir.mkdir(parents=True, exist_ok=True)
        
        self.config_file = self.app_data_dir / CONFIG_FILE_NAME
        self.config = self.load_config()
        
        # Ensure local path exists or set default
        if not self.config.local_path:
            self.config.local_path = str(self.app_data_dir / BACKUP_DIR_NAME)
            self.save_config()
            
        self._ensure_key()
        self.scheduler_thread = None
        self.stop_event = threading.Event()

    def load_config(self) -> BackupConfig:
        if self.config_file.exists():
            try:
                with open(self.config_file, "r") as f:
                    data = json.load(f)
                return BackupConfig.from_dict(data)
            except Exception as e:
                logger.error(f"Failed to load backup config: {e}")
        return BackupConfig()

    def save_config(self):
        try:
            with open(self.config_file, "w") as f:
                json.dump(self.config.to_dict(), f, indent=4)
        except Exception as e:
            logger.error(f"Failed to save backup config: {e}")

    def _ensure_key(self):
        """Ensures an encryption key exists if encryption is enabled."""
        if self.config.encrypt and not self.config.encryption_key:
            if Fernet:
                self.config.encryption_key = Fernet.generate_key().decode()
                self.save_config()
            else:
                logger.warning("Encryption enabled but cryptography module missing.")

    def get_db_path(self) -> Optional[Path]:
        """Extracts DB path from settings."""
        # Check if it's MySQL
        if "mysql" in settings.DB_URL:
            # For MySQL, we don't have a single file path, but we can return a dummy path or None
            # The backup logic will handle the dump.
            return None

        if "sqlite" in settings.DB_URL:
            # format: sqlite:///./fbr_invoices.db
            path_str = settings.DB_URL.replace("sqlite:///", "")
            
            # Resolve relative paths relative to the project root (where run.bat is)
            # or allow absolute paths
            db_path = Path(path_str)
            if not db_path.is_absolute():
                # Assuming app run from project root, or we can find root relative to this file
                project_root = Path(__file__).resolve().parent.parent.parent
                db_path = project_root / path_str
                
            return db_path.resolve()
        return None

    def _get_mysql_config(self) -> Dict:
        """Parses MySQL URL to get connection details."""
        # Format: mysql+pymysql://user:pass@host:port/dbname
        url = urllib.parse.urlparse(settings.DB_URL)
        return {
            "user": urllib.parse.unquote(url.username or "root"),
            "password": urllib.parse.unquote(url.password or ""),
            "host": url.hostname or "localhost",
            "port": url.port or 3306,
            "database": url.path.lstrip('/')
        }
    
    def _find_mysql_tool(self, tool_name: str) -> Optional[str]:
        """Finds mysqldump or mysql executable."""
        # 1. Check PATH
        path_tool = shutil.which(tool_name)
        if path_tool:
            return path_tool
            
        # 2. Check common Laragon paths
        laragon_path = Path("C:/laragon/bin/mysql")
        if laragon_path.exists():
            # Find latest version
            versions = sorted(laragon_path.glob("mysql-*"), reverse=True)
            for v in versions:
                tool_path = v / "bin" / f"{tool_name}.exe"
                if tool_path.exists():
                    return str(tool_path)
        
        return None

    def _backup_mysql(self, backup_dir: Path, backup_name: str) -> Optional[Path]:
        """Performs MySQL dump."""
        config = self._get_mysql_config()
        mysqldump = self._find_mysql_tool("mysqldump")
        
        if not mysqldump:
            raise Exception("mysqldump not found. Please ensure MySQL is installed and accessible.")
            
        sql_file = backup_dir / f"{backup_name}.sql"
        
        # Build command
        cmd = [
            mysqldump,
            "-h", config["host"],
            "-P", str(config["port"]),
            "-u", config["user"],
        ]
        
        if config["password"]:
            cmd.append(f"--password={config['password']}")
            
        cmd.append(config["database"])
        
        try:
            with open(sql_file, "w") as f:
                subprocess.run(cmd, stdout=f, check=True, text=True)
            return sql_file
        except subprocess.CalledProcessError as e:
            logger.error(f"MySQL Dump failed: {e}")
            if sql_file.exists():
                os.remove(sql_file)
            raise Exception(f"MySQL backup failed: {e}")

    def _restore_mysql(self, sql_file: Path):
        """Restores MySQL dump."""
        config = self._get_mysql_config()
        mysql = self._find_mysql_tool("mysql")
        
        if not mysql:
             raise Exception("mysql client not found.")
             
        # Build command
        cmd = [
            mysql,
            "-h", config["host"],
            "-P", str(config["port"]),
            "-u", config["user"],
        ]
        
        if config["password"]:
            cmd.append(f"--password={config['password']}")
            
        cmd.append(config["database"])
        
        try:
            with open(sql_file, "r") as f:
                subprocess.run(cmd, stdin=f, check=True)
        except subprocess.CalledProcessError as e:
             raise Exception(f"MySQL restore failed: {e}")

    def create_backup(self, is_manual: bool = False) -> Dict:
        """Creates a backup of the database."""
        # Determine DB Type
        is_mysql = "mysql" in settings.DB_URL
        
        if not is_mysql:
            # Fallback to SQLite logic
            db_path = self.get_db_path()
            if not db_path or not db_path.exists():
                return {"success": False, "message": "Database file not found."}
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"backup_{timestamp}"
        if is_manual:
            backup_name += "_manual"
            
        backup_dir = Path(self.config.local_path)
        backup_dir.mkdir(parents=True, exist_ok=True)
        
        zip_path = backup_dir / f"{backup_name}.zip"
        enc_path = backup_dir / f"{backup_name}.enc"
        
        try:
            source_file = None
            original_filename = ""
            
            if is_mysql:
                # 1. Create MySQL Dump
                source_file = self._backup_mysql(backup_dir, backup_name)
                original_filename = "dump.sql"
            else:
                source_file = db_path
                original_filename = db_path.name
                
            # 2. Create ZIP
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                zipf.write(source_file, arcname=original_filename)
                # Add metadata
                metadata = {
                    "timestamp": datetime.now().isoformat(),
                    "version": "1.0",
                    "checksum": self._calculate_file_hash(source_file),
                    "original_filename": original_filename,
                    "db_type": "mysql" if is_mysql else "sqlite"
                }
                zipf.writestr("metadata.json", json.dumps(metadata))

            final_path = zip_path
            
            # Cleanup temp SQL dump
            if is_mysql and source_file.exists():
                os.remove(source_file)

            # 3. Encrypt if enabled
            if self.config.encrypt:
                if not Fernet:
                     return {"success": False, "message": "Encryption failed: cryptography module missing."}
                
                fernet = Fernet(self.config.encryption_key.encode())
                with open(zip_path, "rb") as f:
                    data = f.read()
                encrypted = fernet.encrypt(data)
                with open(enc_path, "wb") as f:
                    f.write(encrypted)
                
                # Remove unencrypted zip
                os.remove(zip_path)
                final_path = enc_path

            # 4. Copy to Cloud/Secondary Path
            if self.config.cloud_path:
                cloud_dir = Path(self.config.cloud_path)
                if cloud_dir.exists():
                    shutil.copy2(final_path, cloud_dir / final_path.name)

            # 5. Cleanup old backups
            self._cleanup_old_backups()

            return {"success": True, "message": f"Backup created: {final_path.name}", "path": str(final_path)}

        except Exception as e:
            logger.error(f"Backup failed: {e}")
            return {"success": False, "message": str(e)}

    def restore_backup(self, backup_path_str: str) -> Dict:
        """Restores the database from a backup file."""
        backup_path = Path(backup_path_str)
        if not backup_path.exists():
            return {"success": False, "message": "Backup file not found."}

        is_mysql = "mysql" in settings.DB_URL
        db_path = None
        
        if not is_mysql:
            db_path = self.get_db_path()
            if not db_path:
                 return {"success": False, "message": "Target database path not found."}

        try:
            # Decrypt if needed
            if backup_path.suffix == ".enc":
                if not Fernet:
                     return {"success": False, "message": "Decryption failed: cryptography module missing."}

                if not self.config.encryption_key:
                     return {"success": False, "message": "Encryption key missing."}
                
                fernet = Fernet(self.config.encryption_key.encode())
                with open(backup_path, "rb") as f:
                    encrypted_data = f.read()
                
                decrypted_data = fernet.decrypt(encrypted_data)
                
                # Write to temp zip
                temp_zip = backup_path.with_suffix(".zip.temp")
                with open(temp_zip, "wb") as f:
                    f.write(decrypted_data)
                
                source_zip = temp_zip
            else:
                source_zip = backup_path

            # Verify and Extract
            with zipfile.ZipFile(source_zip, 'r') as zipf:
                if "metadata.json" not in zipf.namelist():
                     return {"success": False, "message": "Invalid backup: Missing metadata."}
                
                metadata = json.loads(zipf.read("metadata.json").decode())
                
                # Check compatibility
                backup_db_type = metadata.get("db_type", "sqlite")
                current_db_type = "mysql" if is_mysql else "sqlite"
                if backup_db_type != current_db_type:
                     return {"success": False, "message": f"Backup type mismatch. Backup is {backup_db_type}, but current DB is {current_db_type}."}

                original_filename = metadata.get("original_filename", "dump.sql" if is_mysql else db_path.name)
                
                if is_mysql:
                    # Restore MySQL
                    # Extract SQL to temp location
                    temp_dir = backup_path.parent / "restore_temp"
                    temp_dir.mkdir(exist_ok=True)
                    zipf.extract(original_filename, path=temp_dir)
                    sql_file = temp_dir / original_filename
                    
                    try:
                        self._restore_mysql(sql_file)
                    finally:
                        if sql_file.exists():
                            os.remove(sql_file)
                        if temp_dir.exists():
                            shutil.rmtree(temp_dir)
                else:
                    # Restore SQLite
                    # Backup current DB before overwriting (Safety net)
                    if db_path.exists():
                        safety_backup = db_path.with_suffix(".bak.safety")
                        shutil.copy2(db_path, safety_backup)
                    
                    # Extract
                    zipf.extract(original_filename, path=db_path.parent)
                    
                    # Verify Checksum
                    restored_hash = self._calculate_file_hash(db_path)
                    if restored_hash != metadata.get("checksum"):
                        # Rollback
                        if db_path.exists():
                             shutil.copy2(db_path.with_suffix(".bak.safety"), db_path)
                        return {"success": False, "message": "Integrity check failed! Backup corrupted."}

            # Cleanup temp
            if backup_path.suffix == ".enc" and source_zip.exists():
                os.remove(source_zip)

            return {"success": True, "message": "Restore successful."}

        except Exception as e:
            logger.error(f"Restore failed: {e}")
            return {"success": False, "message": str(e)}

    def _calculate_file_hash(self, filepath: Path) -> str:
        sha256_hash = hashlib.sha256()
        with open(filepath, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()

    def _cleanup_old_backups(self):
        """Deletes backups older than retention_days."""
        if self.config.retention_days <= 0:
            return

        backup_dir = Path(self.config.local_path)
        cutoff = datetime.now() - timedelta(days=self.config.retention_days)
        
        for file in backup_dir.glob("backup_*"):
            if file.stat().st_mtime < cutoff.timestamp():
                try:
                    os.remove(file)
                    logger.info(f"Deleted old backup: {file.name}")
                except Exception as e:
                    logger.error(f"Failed to delete old backup {file.name}: {e}")

    def list_backups(self) -> List[Dict]:
        """Lists available backups."""
        backup_dir = Path(self.config.local_path)
        if not backup_dir.exists():
            return []
            
        backups = []
        for file in backup_dir.glob("backup_*"):
            try:
                stat = file.stat()
                backups.append({
                    "name": file.name,
                    "path": str(file),
                    "size_mb": round(stat.st_size / (1024 * 1024), 2),
                    "date": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
                })
            except Exception:
                pass
        
        # Sort by date desc
        return sorted(backups, key=lambda x: x["date"], reverse=True)

    # --- Scheduling ---
    def start_scheduler(self):
        if not schedule:
            logger.warning("Schedule module missing. Automatic backups disabled.")
            return

        if not self.config.enabled:
            return
            
        if self.scheduler_thread and self.scheduler_thread.is_alive():
            return

        self.stop_event.clear()
        
        # Clear existing jobs
        schedule.clear()
        
        # Setup job
        if self.config.interval == "daily":
            schedule.every().day.at(self.config.time_str).do(self.create_backup)
        elif self.config.interval == "weekly":
            schedule.every().monday.at(self.config.time_str).do(self.create_backup)
        elif self.config.interval == "monthly":
            # Schedule doesn't support monthly directly easily, stick to 30 days or logic
            schedule.every(30).days.at(self.config.time_str).do(self.create_backup)

        self.scheduler_thread = threading.Thread(target=self._run_scheduler, daemon=True)
        self.scheduler_thread.start()
        logger.info("Backup scheduler started.")

    def stop_scheduler(self):
        self.stop_event.set()
        if self.scheduler_thread:
            self.scheduler_thread.join(timeout=1)
        logger.info("Backup scheduler stopped.")

    def _run_scheduler(self):
        if not schedule:
            return
        while not self.stop_event.is_set():
            schedule.run_pending()
            time.sleep(60)

# Singleton instance
backup_service = BackupService()
