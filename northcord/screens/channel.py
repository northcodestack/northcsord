from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import Header, Footer, Label
from textual.containers import Vertical, Horizontal

from northcord.widgets.message import MessageList
from northcord.widgets.input import MessageInput
from northcord.widgets.header import NorthCordHeader


class ChannelScreen(Screen):
    BINDINGS = [
        Binding("escape", "back", "Back"),
        Binding("ctrl+r", "reply", "Reply"),
        Binding("ctrl+u", "upload", "Upload"),
    ]

    def __init__(self, channel_id: str, channel_name: str, **kwargs):
        super().__init__(**kwargs)
        self.channel_id = channel_id
        self.channel_name = channel_name

    def compose(self) -> ComposeResult:
        yield NorthCordHeader()
        yield Horizontal(
            Vertical(
                Label(f"#{self.channel_name}", id="channel-label"),
                id="channel-info",
            ),
            Vertical(
                MessageList(id="channel-message-list"),
                MessageInput(id="channel-message-input"),
                id="channel-main",
            ),
        )
        yield Footer()

    def action_back(self) -> None:
        self.dismiss()

    def action_reply(self) -> None:
        msg_list = self.query_one("#channel-message-list", MessageList)
        msg_list.start_reply()

    def action_upload(self) -> None:
        msg_input = self.query_one("#channel-message-input", MessageInput)
        msg_input.upload_file()

    def on_mount(self) -> None:
        self.query_one("#channel-message-input", MessageInput).focus()
