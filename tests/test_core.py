from __future__ import annotations

import unittest
from unittest.mock import Mock, patch

from northcord.utils.config import Config
from northcord.core.commands import CommandHandler
from northcord.core.discord import DiscordClient
from northcord.core.audio import AudioProcessor


import os
import tempfile

class TestConfig(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = os.path.join(self.temp_dir.name, "config.json")
        self.config = Config(self.temp_path)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_default_values(self):
        self.assertEqual(self.config.get("theme"), "dark")
        self.assertEqual(self.config.get("voice.enabled"), True)
        self.assertEqual(self.config.get("notifications.mentions_only"), True)

    def test_set_and_get(self):
        self.config.set("theme", "light")
        self.assertEqual(self.config.get("theme"), "light")

    def test_set_nested(self):
        self.config.set("voice.push_to_talk", False)
        self.assertEqual(self.config.get("voice.push_to_talk"), False)

    def test_get_default(self):
        self.assertEqual(self.config.get("nonexistent", "fallback"), "fallback")
        self.assertIsNone(self.config.get("nonexistent"))


class TestCommands(unittest.TestCase):
    def setUp(self):
        self.app = Mock()
        self.app.discord = Mock()
        self.app.gateway = Mock()
        self.handler = CommandHandler(self.app)

    def test_help_command(self):
        result = self.handler.execute("/help")
        self.assertIsNotNone(result)
        self.assertIn("NorthCord Commands", result)

    def test_unknown_command(self):
        result = self.handler.execute("/nonexistent")
        self.assertIsNotNone(result)
        self.assertIn("Unknown command", result)

    def test_non_command(self):
        result = self.handler.execute("hello world")
        self.assertIsNone(result)

    def test_empty_input(self):
        result = self.handler.execute("/")
        self.assertIsNone(result)

    def test_theme_command_no_args(self):
        result = self.handler.execute("/theme")
        self.assertIn("Usage", result)

    def test_custom_command(self):
        called = False

        def my_handler(args):
            nonlocal called
            called = True
            return "done"

        self.handler.register("test", my_handler)
        result = self.handler.execute("/test arg1 arg2")
        self.assertEqual(result, "done")
        self.assertTrue(called)


class TestDiscordClient(unittest.TestCase):
    @patch("northcord.core.discord.requests.Session")
    def test_initialization(self, mock_session):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = os.path.join(temp_dir, "config.json")
            config = Config(temp_path)
            config.set("token", "test_token")
            client = DiscordClient(config)
            self.assertIsNotNone(client)

    def test_no_token(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = os.path.join(temp_dir, "config.json")
            config = Config(temp_path)
            client = DiscordClient(config)
            self.assertIsNone(client.token)


class TestAudioProcessor(unittest.TestCase):
    def setUp(self):
        self.processor = AudioProcessor()

    def test_initialization(self):
        self.assertIsNotNone(self.processor)

    def test_vad_threshold(self):
        self.processor.set_vad_threshold(0.8)
        self.assertEqual(self.processor._vad_threshold, 0.8)

    def test_vad_threshold_clamp(self):
        self.processor.set_vad_threshold(2.0)
        self.assertEqual(self.processor._vad_threshold, 1.0)
        self.processor.set_vad_threshold(-0.5)
        self.assertEqual(self.processor._vad_threshold, 0.0)


if __name__ == "__main__":
    unittest.main()
