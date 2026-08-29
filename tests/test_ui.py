from __future__ import annotations

import unittest
from unittest.mock import Mock, patch

from northcord.themes.dark import DarkTheme
from northcord.themes.light import LightTheme
from northcord.widgets.message import MessageWidget, MessageList
from northcord.widgets.header import NorthCordHeader
from northcord.utils.helpers import format_timestamp, truncate, sanitize_input


class TestDarkTheme(unittest.TestCase):
    def setUp(self):
        self.theme = DarkTheme()

    def test_theme_name(self):
        self.assertEqual(self.theme.name, "dark")

    def test_colors_exist(self):
        colors = self.theme.get_colors()
        required = ["background", "surface", "primary", "text", "border"]
        for r in required:
            self.assertIn(r, colors)

    def test_all_colors_are_hex(self):
        colors = self.theme.get_colors()
        for value in colors.values():
            self.assertTrue(value.startswith("#"), f"Color {value} is not hex")


class TestLightTheme(unittest.TestCase):
    def setUp(self):
        self.theme = LightTheme()

    def test_theme_name(self):
        self.assertEqual(self.theme.name, "light")

    def test_colors_differ_from_dark(self):
        light_colors = self.theme.get_colors()
        dark = DarkTheme().get_colors()
        self.assertNotEqual(light_colors["background"], dark["background"])


class TestHelpers(unittest.TestCase):
    def test_format_timestamp_empty(self):
        self.assertEqual(format_timestamp(""), "")

    def test_truncate_short(self):
        self.assertEqual(truncate("hello"), "hello")

    def test_truncate_long(self):
        text = "a" * 100
        result = truncate(text, max_length=10)
        self.assertLessEqual(len(result), 10)

    def test_sanitize_input(self):
        self.assertEqual(sanitize_input("  hello  world  "), "hello world")
        self.assertEqual(sanitize_input("hello\x00world"), "helloworld")


class TestMessageWidget(unittest.TestCase):
    def test_widget_creation(self):
        widget = MessageWidget(author="TestUser", content="Hello, world!")
        self.assertIsNotNone(widget)
        self.assertEqual(widget._author, "TestUser")
        self.assertEqual(widget._content, "Hello, world!")

    def test_widget_with_timestamp(self):
        widget = MessageWidget(
            author="User",
            content="Message",
            timestamp="2024-01-01T12:00:00+00:00",
        )
        self.assertIsNotNone(widget)

    def test_widget_reply(self):
        widget = MessageWidget(
            author="User",
            content="Reply message",
            is_reply=True,
            reply_to="OriginalUser",
        )
        self.assertTrue(widget._is_reply)
        self.assertEqual(widget._reply_to, "OriginalUser")


class TestMessageList(unittest.TestCase):
    def setUp(self):
        self.msg_list = MessageList()

    def test_add_message(self):
        self.msg_list.add_message(
            author="TestUser",
            content="Test message",
            message_id="123",
        )
        self.assertEqual(len(self.msg_list._messages), 1)

    def test_clear_messages(self):
        self.msg_list.add_message(author="User", content="Msg")
        self.msg_list.clear_messages()
        self.assertEqual(len(self.msg_list._messages), 0)

    def test_load_messages(self):
        messages = [
            {
                "author": {"username": "User1", "global_name": "User One"},
                "content": "Hello!",
                "id": "1",
                "timestamp": "2024-01-01T00:00:00+00:00",
            },
            {
                "author": {"username": "User2"},
                "content": "Hi!",
                "id": "2",
                "timestamp": "2024-01-01T00:01:00+00:00",
            },
        ]
        self.msg_list.load_messages(messages)
        self.assertEqual(len(self.msg_list._messages), 2)
        self.assertEqual(self.msg_list._messages[0]["author"], "User2")
        self.assertEqual(self.msg_list._messages[1]["author"], "User One")


if __name__ == "__main__":
    unittest.main()
