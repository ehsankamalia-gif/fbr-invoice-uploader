import subprocess
import logging
import os
import sys

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class UpdateService:
    def __init__(self, repo_path=None):
        """
        Initialize the UpdateService.
        :param repo_path: Path to the git repository. Defaults to the current working directory.
        """
        self.repo_path = repo_path if repo_path else os.getcwd()

    def _run_git_command(self, args):
        """
        Helper to run git commands.
        """
        try:
            # Hide console window on Windows
            startupinfo = None
            if sys.platform == "win32":
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = subprocess.SW_HIDE

            # Ensure we are in the repo directory
            result = subprocess.run(
                ["git"] + args,
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=True,
                startupinfo=startupinfo
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
        Checks if updates are available by fetching from remote and comparing HEAD.
        :return: (bool, str) - (Update Available, Message)
        """
        try:
            # 1. Fetch latest changes
            logger.info("Fetching updates from remote...")
            self._run_git_command(["fetch"])

            # 2. Get current branch name
            branch = self._run_git_command(["rev-parse", "--abbrev-ref", "HEAD"])
            
            # 3. Check status relative to upstream
            # status format: "## main...origin/main [behind 2]"
            status = self._run_git_command(["status", "-sb"])
            
            if "behind" in status:
                return True, f"Updates available on branch '{branch}'."
            elif "ahead" in status:
                return False, f"Your version is ahead of remote '{branch}'."
            else:
                return False, "You are using the latest version."
                
        except Exception as e:
            return False, str(e)

    def perform_update(self):
        """
        Pulls the latest changes.
        :return: (bool, str) - (Success, Message)
        """
        try:
            logger.info("Pulling latest changes...")
            output = self._run_git_command(["pull"])
            return True, f"Update successful!\n\n{output}"
        except Exception as e:
            return False, f"Update failed: {str(e)}"

    def get_current_version(self):
        """
        Returns the current commit hash (short).
        """
        try:
            return self._run_git_command(["rev-parse", "--short", "HEAD"])
        except:
            return "Unknown"
