import subprocess
import logging
import os
import sys
import requests
import webbrowser
from packaging import version
try:
    from app.version import __version__ as current_version
except ImportError:
    current_version = "0.0.0"

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

GITHUB_REPO_OWNER = "ehsankamalia-gif"
GITHUB_REPO_NAME = "fbr-invoice-uploader"
GITHUB_API_URL = f"https://api.github.com/repos/{GITHUB_REPO_OWNER}/{GITHUB_REPO_NAME}/releases/latest"

class UpdateService:
    def __init__(self, repo_path=None):
        """
        Initialize the UpdateService.
        :param repo_path: Path to the git repository. Defaults to the current working directory.
        """
        self.repo_path = repo_path if repo_path else os.getcwd()
        self.is_frozen = getattr(sys, 'frozen', False)

    def _run_git_command(self, args):
        """
        Helper to run git commands.
        """
        try:
            # Ensure we are in the repo directory
            result = subprocess.run(
                ["git"] + args,
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            logger.error(f"Git command failed: {e.cmd}. Error: {e.stderr}")
            raise Exception(f"Git error: {e.stderr.strip()}")
        except FileNotFoundError:
            logger.error("Git executable not found.")
            raise Exception("Git is not installed or not in PATH.")

    def check_for_updates(self):
        """
        Checks if updates are available.
        - If frozen (EXE), checks GitHub Releases.
        - If script, checks Git remote.
        :return: (bool, str, str) - (Update Available, Message, Download URL or None)
        """
        if self.is_frozen:
            return self._check_github_updates()
        else:
            is_avail, msg = self._check_git_updates()
            return is_avail, msg, None

    def _check_github_updates(self):
        """Check for updates via GitHub API."""
        try:
            response = requests.get(GITHUB_API_URL, timeout=10)
            if response.status_code == 200:
                data = response.json()
                latest_tag = data.get("tag_name", "v0.0.0").lstrip("v")
                
                # Get download URL for the EXE asset
                download_url = None
                for asset in data.get("assets", []):
                    if asset["name"].endswith(".exe"):
                        download_url = asset["browser_download_url"]
                        break
                
                # Compare versions
                if version.parse(latest_tag) > version.parse(current_version):
                    if download_url:
                        return True, f"New version {latest_tag} is available!\nCurrent version: {current_version}", download_url
                    else:
                        return True, f"New version {latest_tag} is available, but no EXE found.", data.get("html_url")
                else:
                    return False, f"You are using the latest version ({current_version}).", None
            elif response.status_code == 404:
                return False, "Repository not found or is Private.\nPlease make the repository Public on GitHub for updates to work.", None
            else:
                return False, f"Failed to check updates (GitHub API: {response.status_code})", None
        except Exception as e:
            return False, f"Update check failed: {str(e)}", None

    def download_update(self, url, progress_callback=None):
        """
        Downloads the update from the given URL.
        :param url: The URL to download the file from.
        :param progress_callback: A function that takes (current_bytes, total_bytes)
        :return: Path to the downloaded file
        """
        try:
            response = requests.get(url, stream=True)
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            block_size = 1024 # 1 KB
            
            # Save as a temporary file
            new_exe_path = "update_temp.exe"
            
            downloaded = 0
            with open(new_exe_path, 'wb') as f:
                for data in response.iter_content(block_size):
                    downloaded += len(data)
                    f.write(data)
                    if progress_callback:
                        progress_callback(downloaded, total_size)
                        
            return new_exe_path
        except Exception as e:
            logger.error(f"Download failed: {e}")
            raise e

    def apply_update(self, new_exe_path):
        """
        Replaces the current executable with the new one using a batch script.
        """
        if not self.is_frozen:
            logger.error("Cannot apply update: Not running as an executable.")
            return False

        current_exe = sys.executable
        updater_script = "updater.bat"
        
        # Create a batch script to replace the EXE
        # 1. Wait for current app to close
        # 2. Delete current EXE
        # 3. Rename new EXE to current EXE name
        # 4. Start the new EXE
        
        script_content = f"""
@echo off
timeout /t 2 /nobreak >nul
del "{current_exe}"
move "{new_exe_path}" "{current_exe}"
start "" "{current_exe}"
del "%~f0"
"""
        with open(updater_script, "w") as f:
            f.write(script_content)
            
        # Run the script and exit
        subprocess.Popen(updater_script, shell=True)
        sys.exit(0)


    def _check_git_updates(self):
        """Check for updates via Git."""
        try:
            # 1. Fetch latest changes
            logger.info("Fetching updates from remote...")
            self._run_git_command(["fetch"])

            # 2. Get current branch name
            branch = self._run_git_command(["rev-parse", "--abbrev-ref", "HEAD"])
            
            # 3. Check status relative to upstream
            status = self._run_git_command(["status", "-sb"])
            
            if "behind" in status:
                return True, f"Updates available on branch '{branch}'."
            elif "ahead" in status:
                return False, f"Your version is ahead of remote '{branch}'."
            else:
                return False, "You are using the latest version (Git)."
                
        except Exception as e:
            return False, f"Git update check failed: {str(e)}"

    def perform_update(self):
        """
        Performs the update.
        - If frozen: Opens the release page.
        - If script: Pulls git changes.
        :return: (bool, str) - (Success, Message)
        """
        if self.is_frozen:
            try:
                release_url = f"https://github.com/{GITHUB_REPO_OWNER}/{GITHUB_REPO_NAME}/releases/latest"
                webbrowser.open(release_url)
                return True, "Opened download page in your browser."
            except Exception as e:
                return False, f"Failed to open browser: {str(e)}"
        else:
            try:
                logger.info("Pulling latest changes...")
                output = self._run_git_command(["pull"])
                return True, f"Update successful!\n\n{output}"
            except Exception as e:
                return False, f"Update failed: {str(e)}"

    def get_current_version(self):
        """
        Returns the current version or commit hash.
        """
        if self.is_frozen:
            return current_version
        else:
            try:
                return self._run_git_command(["rev-parse", "--short", "HEAD"])
            except:
                return "Unknown"
