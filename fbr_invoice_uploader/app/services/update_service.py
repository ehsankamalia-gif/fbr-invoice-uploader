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
        :return: (bool, str) - (Update Available, Message)
        """
        if self.is_frozen:
            return self._check_github_updates()
        else:
            return self._check_git_updates()

    def _check_github_updates(self):
        """Check for updates via GitHub API."""
        try:
            response = requests.get(GITHUB_API_URL, timeout=10)
            if response.status_code == 200:
                data = response.json()
                latest_tag = data.get("tag_name", "v0.0.0").lstrip("v")
                
                # Compare versions
                if version.parse(latest_tag) > version.parse(current_version):
                    return True, f"New version {latest_tag} is available!\nCurrent version: {current_version}"
                else:
                    return False, f"You are using the latest version ({current_version})."
            elif response.status_code == 404:
                return False, "No public releases found for this application."
            else:
                return False, f"Failed to check updates (GitHub API: {response.status_code})"
        except Exception as e:
            return False, f"Update check failed: {str(e)}"

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
