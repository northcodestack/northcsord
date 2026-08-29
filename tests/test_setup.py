from __future__ import annotations

import json
import os
import tempfile
import unittest
from unittest.mock import Mock, patch

from northcord.setup import SetupManager
from northcord.utils.config import ConfigManager


class TestSetupAndConfig(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.config_path = os.path.join(self.temp_dir.name, "config.json")
        self.config = ConfigManager(self.config_path)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_config_reset(self):
        # Set some custom values
        self.config.set("theme", "solarized")
        self.config.set("volume", 90)
        self.assertEqual(self.config.get("theme"), "solarized")
        self.assertEqual(self.config.get("volume"), 90)

        # Reset
        success = self.config.reset_config()
        self.assertTrue(success)
        self.assertEqual(self.config.get("theme"), "dark")
        self.assertEqual(self.config.get("volume"), 75)

    def test_config_export_import(self):
        # Set values and export
        self.config.set("theme", "monokai")
        self.config.set("volume", 40)
        export_path = os.path.join(self.temp_dir.name, "export.json")
        
        success_export = self.config.export_config(export_path)
        self.assertTrue(success_export)
        self.assertTrue(os.path.exists(export_path))

        # Reset config to clear values
        self.config.reset_config()
        self.assertEqual(self.config.get("theme"), "dark")

        # Import values
        success_import = self.config.import_config(export_path)
        self.assertTrue(success_import)
        self.assertEqual(self.config.get("theme"), "monokai")
        self.assertEqual(self.config.get("volume"), 40)

    @patch("northcord.setup.DiscordClient")
    def test_setup_manager_defaults(self, mock_discord_client):
        # Mock validation to return True
        mock_instance = Mock()
        mock_instance.validate_token = Mock(return_value=True)
        # Handle async validation
        async def mock_validate():
            return True
        mock_instance.validate_token = mock_validate
        mock_discord_client.return_value = mock_instance

        # Run setup defaults wizard
        setup = SetupManager(
            config_path=self.config_path,
            token="test_token_valid_for_defaults",
            defaults=True
        )
        success = setup.run_wizard()
        
        self.assertTrue(success)
        self.config.load_config()
        self.assertEqual(self.config.get_token(), "test_token_valid_for_defaults")
        self.assertEqual(self.config.get("theme"), "dark")
        self.assertEqual(self.config.get("volume"), 75)

    @patch("northcord.setup.DiscordClient")
    def test_setup_manager_quick(self, mock_discord_client):
        # Mock validation
        mock_instance = Mock()
        async def mock_validate():
            return True
        async def mock_get_user():
            return {"username": "QuickTestUser"}
        mock_instance.validate_token = mock_validate
        mock_instance.get_user = mock_get_user
        mock_discord_client.return_value = mock_instance

        # Run quick setup
        setup = SetupManager(
            config_path=self.config_path,
            token="test_quick_token",
            theme="midnight",
            volume=85,
            quick=True
        )
        success = setup.run_wizard()
        
        self.assertTrue(success)
        # Reload configuration
        self.config.load_config()
        self.assertEqual(self.config.get_token(), "test_quick_token")
        self.assertEqual(self.config.get("theme"), "midnight")
        self.assertEqual(self.config.get("volume"), 85)


if __name__ == "__main__":
    unittest.main()
