import json
import os

class UrlManager:
    CONFIG_FILE = "portal_config.json"
    DEFAULT_URL = "https://dealers.ahlportal.com"

    def __init__(self):
        self.config_path = os.path.join(os.getcwd(), self.CONFIG_FILE)

    def get_default_url(self):
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r') as f:
                    data = json.load(f)
                    return data.get('url', self.DEFAULT_URL)
            except Exception:
                pass
        return self.DEFAULT_URL

    def save_default_url(self, url):
        try:
            with open(self.config_path, 'w') as f:
                json.dump({'url': url}, f)
            return True
        except Exception:
            return False

    def save_as_shortcut(self, url, filename):
        """Creates a .url internet shortcut file."""
        try:
            with open(filename, 'w') as f:
                f.write('[InternetShortcut]\n')
                f.write(f'URL={url}\n')
            return True
        except Exception as e:
            raise e
