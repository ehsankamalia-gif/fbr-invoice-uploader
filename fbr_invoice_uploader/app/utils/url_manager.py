import os
import json
import sys

class UrlManager:
    def __init__(self, config_file="user_settings.json"):
        # Ensure we look for the file in the project root, not just CWD
        # File is at: app/utils/url_manager.py
        # We want to go up to fbr_invoice_uploader/ (project root)
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.abspath(os.path.join(current_dir, "../../"))
        self.config_file = os.path.join(project_root, config_file)

    def save_default_url(self, url):
        """Saves the URL to a local JSON config file."""
        settings = {}
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    settings = json.load(f)
            except:
                pass
        
        settings['default_portal_url'] = url
        
        with open(self.config_file, 'w') as f:
            json.dump(settings, f, indent=4)
            
    def get_default_url(self):
        """Retrieves the saved URL from local config."""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    settings = json.load(f)
                    return settings.get('default_portal_url')
            except:
                pass
        return None

    def save_as_shortcut(self, url, file_path):
        """Saves the URL as a .url internet shortcut file."""
        if not file_path.endswith('.url'):
            file_path += '.url'
            
        content = f"[InternetShortcut]\nURL={url}\n"
        
        with open(file_path, 'w') as f:
            f.write(content)
        return file_path
