from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import Header, Footer, Tree, Label
from textual.containers import Vertical, Horizontal

from northcord.widgets.message import MessageList
from northcord.widgets.input import MessageInput
from northcord.widgets.header import NorthCordHeader


class ServerScreen(Screen):
    BINDINGS = [
        Binding("escape", "back", "Back"),
    ]

    def __init__(self, server_id: str, server_name: str, **kwargs):
        super().__init__(**kwargs)
        self.server_id = server_id
        self.server_name = server_name

    def compose(self) -> ComposeResult:
        yield NorthCordHeader()
        yield Horizontal(
            Vertical(
                Label(f"#{self.server_name}", id="server-label"),
                Tree("Channels", id="channel-tree"),
                id="server-sidebar",
            ),
            Vertical(
                MessageList(id="server-message-list"),
                MessageInput(id="server-message-input"),
                id="server-main",
            ),
        )
        yield Footer()

    def action_back(self) -> None:
        self.dismiss()

    def on_mount(self) -> None:
        self.query_one("#server-message-input", MessageInput).focus()
