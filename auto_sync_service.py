import sys
import time
import subprocess
import os
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# Configuration
WATCH_DIR = "."
DEBOUNCE_SECONDS = 1  # Sync 1 second after save (Immediate)
IGNORE_DIRS = {'.git', '.venv', 'venv', '__pycache__', 'dist', 'build', '.idea', '.vscode'}
IGNORE_EXTENSIONS = {'.pyc', '.pyd', '.log', '.tmp'}

class GitAutoSyncHandler(FileSystemEventHandler):
    def __init__(self):
        self.last_change_time = 0
        self.pending_sync = False

    def on_any_event(self, event):
        # Filter out ignored directories and files
        path_parts = os.path.normpath(event.src_path).split(os.sep)
        
        # Check if any part of the path is in IGNORE_DIRS
        for part in path_parts:
            if part in IGNORE_DIRS:
                return

        # Check extensions
        _, ext = os.path.splitext(event.src_path)
        if ext in IGNORE_EXTENSIONS:
            return

        print(f"Change detected: {event.src_path}")
        self.last_change_time = time.time()
        self.pending_sync = True

def sync_to_github():
    print("\n[Auto-Sync] Starting synchronization...")
    try:
        # 1. Add Changes
        subprocess.run(["git", "add", "."], check=True)
        
        # 2. Commit (if changes exist)
        # Check if there are changes to commit
        status = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True)
        if not status.stdout.strip():
            print("[Auto-Sync] No changes to commit.")
            return

        commit_msg = f"Auto-sync: {time.strftime('%Y-%m-%d %H:%M:%S')}"
        subprocess.run(["git", "commit", "-m", commit_msg], check=True)
        
        # 3. Pull (Fetch + Merge) to ensure we are up to date
        print("[Auto-Sync] Pulling latest changes from GitHub...")
        try:
            # use --no-edit to avoid opening a text editor for merge messages
            # use -X ours to automatically resolve conflicts by keeping LOCAL changes
            subprocess.run(["git", "pull", "--no-edit", "-X", "ours", "origin", "main"], check=True)
        except subprocess.CalledProcessError:
            print("[Auto-Sync] Pull failed! Trying to force sync...")
            return

        # 4. Push
        # Note: The post-commit hook might have already pushed, but we ensure it here.
        print("[Auto-Sync] Pushing to GitHub...")
        subprocess.run(["git", "push", "origin", "main"], check=True)
        print("[Auto-Sync] Synchronization Complete!\n")
        
    except subprocess.CalledProcessError as e:
        print(f"[Auto-Sync] Error during sync: {e}")
    except Exception as e:
        print(f"[Auto-Sync] Unexpected error: {e}")

if __name__ == "__main__":
    event_handler = GitAutoSyncHandler()
    observer = Observer()
    observer.schedule(event_handler, WATCH_DIR, recursive=True)
    observer.start()
    
    print(f"Monitoring {os.path.abspath(WATCH_DIR)} for changes...")
    print(f"Press Ctrl+C to stop.")

    try:
        while True:
            time.sleep(1)
            if event_handler.pending_sync:
                # Check if debounce time has passed
                if time.time() - event_handler.last_change_time >= DEBOUNCE_SECONDS:
                    sync_to_github()
                    event_handler.pending_sync = False
    except KeyboardInterrupt:
        observer.stop()
    
    observer.join()
