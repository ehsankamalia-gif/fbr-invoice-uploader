import unittest
import os
import json
import sys

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from app.utils.url_manager import UrlManager

class TestUrlManager(unittest.TestCase):
    def setUp(self):
        self.test_config = "test_settings.json"
        self.manager = UrlManager(self.test_config)
        
    def tearDown(self):
        if os.path.exists(self.test_config):
            os.remove(self.test_config)
        if os.path.exists("test_shortcut.url"):
            os.remove("test_shortcut.url")

    def test_save_and_get_default_url(self):
        url = "https://example.com"
        self.manager.save_default_url(url)
        
        loaded_url = self.manager.get_default_url()
        self.assertEqual(url, loaded_url)
        
        # Verify file content
        with open(self.test_config, 'r') as f:
            data = json.load(f)
            self.assertEqual(data['default_portal_url'], url)

    def test_save_as_shortcut(self):
        url = "https://google.com"
        path = "test_shortcut"
        created_path = self.manager.save_as_shortcut(url, path)
        
        self.assertTrue(os.path.exists(created_path))
        self.assertTrue(created_path.endswith(".url"))
        
        with open(created_path, 'r') as f:
            content = f.read()
            self.assertIn("[InternetShortcut]", content)
            self.assertIn(f"URL={url}", content)

if __name__ == '__main__':
    unittest.main()
