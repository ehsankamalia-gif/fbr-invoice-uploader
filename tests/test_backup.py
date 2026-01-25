import pytest
import os
import json
import shutil
from pathlib import Path
from app.services.backup_service import BackupService, BackupConfig
import time

# Helper to mock DB
@pytest.fixture
def mock_db_file(tmp_path):
    db_file = tmp_path / "fbr_invoices.db"
    db_file.write_text("Dummy DB Content")
    return db_file

@pytest.fixture
def backup_service_instance(tmp_path, mock_db_file):
    # Monkeypatch settings to point to tmp_path
    service = BackupService()
    service.app_data_dir = tmp_path / "app_data"
    service.app_data_dir.mkdir()
    service.config_file = service.app_data_dir / "backup_config.json"
    
    # Mock get_db_path
    service.get_db_path = lambda: mock_db_file
    
    # Reset config
    service.config = BackupConfig(local_path=str(tmp_path / "backups"), encrypt=True, encryption_key="")
    service._ensure_key()
    service.save_config()
    
    return service

def test_config_persistence(backup_service_instance):
    service = backup_service_instance
    service.config.interval = "weekly"
    service.save_config()
    
    # Reload
    new_service = BackupService()
    new_service.config_file = service.config_file
    loaded_config = new_service.load_config()
    
    assert loaded_config.interval == "weekly"
    assert loaded_config.encrypt is True
    assert loaded_config.encryption_key == service.config.encryption_key

def test_create_backup(backup_service_instance):
    service = backup_service_instance
    res = service.create_backup(is_manual=True)
    
    assert res["success"] is True
    assert "path" in res
    assert Path(res["path"]).exists()
    assert Path(res["path"]).suffix == ".enc"

def test_restore_backup(backup_service_instance, mock_db_file):
    service = backup_service_instance
    
    # Modify original DB
    mock_db_file.write_text("Original Content")
    
    # Backup
    res = service.create_backup()
    assert res["success"] is True
    backup_path = res["path"]
    
    # Corrupt DB
    mock_db_file.write_text("Corrupted Content")
    
    # Restore
    res = service.restore_backup(backup_path)
    assert res["success"] is True, res["message"]
    
    # Verify content
    assert mock_db_file.read_text() == "Original Content"

def test_retention_policy(backup_service_instance):
    service = backup_service_instance
    service.config.retention_days = 0 # Should delete everything if logic was strict, but code says <=0 returns.
    # Let's test actual deletion
    service.config.retention_days = 1
    
    backup_dir = Path(service.config.local_path)
    backup_dir.mkdir(parents=True, exist_ok=True)
    
    # Create old file
    old_file = backup_dir / "backup_old_2020.zip"
    old_file.touch()
    # Set time to 2 days ago
    two_days_ago = time.time() - (2 * 24 * 3600)
    os.utime(old_file, (two_days_ago, two_days_ago))
    
    # Create new file
    new_file = backup_dir / "backup_new_2024.zip"
    new_file.touch()
    
    service._cleanup_old_backups()
    
    assert not old_file.exists()
    assert new_file.exists()
