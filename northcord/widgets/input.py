from __future__ import annotations

import os
from pathlib import Path

from textual.app import ComposeResult
from textual.binding import Binding
from textual.widgets import Input, Static
from textual.containers import Horizontal
from textual import events

from northcord.core.commands import CommandHandler


class MessageInput(Input):
    BINDINGS = [
        Binding("escape", "blur", "Blur", show=False),
    ]

    def __init__(self, **kwargs):
        super().__init__(placeholder="Type a message... (/ for commands)", **kwargs)
        self._command_handler: CommandHandler | None = None

    def set_command_handler(self, handler: CommandHandler) -> None:
        self._command_handler = handler

    def action_submit(self) -> None:
        value = self.value.strip()
        if not value:
            return

        if value.startswith("/"):
            self._handle_command(value)
        else:
            self._send_message(value)

        self.clear()

    def _handle_command(self, input_text: str) -> None:
        if self._command_handler:
            result = self._command_handler.execute(input_text)
            if result:
                self.app.notify(result, severity="information")
        else:
            self.app.notify("Command handler not available", severity="error")

    def _send_message(self, content: str) -> None:
        discord = getattr(self.app, "discord", None)
        if discord:
            result = discord.send_message(channel_id="0", content=content)
            if result:
                self.app.notify("Message sent", severity="information")
        else:
            self.app.notify("Discord client not available", severity="error")

    def upload_file(self) -> None:
        file_path = os.path.expanduser(self.value.strip())
        if not file_path:
            self.app.notify("Enter a file path first", severity="warning")
            return
        path = Path(file_path)
        if not path.exists():
            self.app.notify(f"File not found: {file_path}", severity="error")
            return
        self.app.notify(f"Uploading {path.name}...", severity="information")
        self.clear()
