from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import Header, Footer
from textual.containers import Horizontal

from northcord.widgets.sidebar import ServerSidebar, ChannelSidebar
from northcord.widgets.message import MessageList
from northcord.widgets.input import MessageInput
from northcord.widgets.header import NorthCordHeader


class MainScreen(Screen):
    BINDINGS = [
        Binding("tab", "focus_next_pane", "Next Pane", show=False),
        Binding("shift+tab", "focus_previous_pane", "Previous Pane", show=False),
        Binding("/", "focus_input", "Focus Input", show=False),
    ]

    def compose(self) -> ComposeResult:
        yield NorthCordHeader()
        yield Horizontal(
            ServerSidebar(id="server-sidebar"),
            ChannelSidebar(id="channel-sidebar"),
            MessageList(id="message-list"),
        )
        yield MessageInput(id="message-input")
        yield Footer()

    def on_mount(self) -> None:
        self.query_one("#message-input", MessageInput).focus()

    def action_focus_input(self) -> None:
        self.query_one("#message-input", MessageInput).focus()

    def action_focus_next_pane(self) -> None:
        self.focus_next()

    def action_focus_previous_pane(self) -> None:
        self.focus_previous()

    def action_quick_switcher(self) -> None:
        self.app.action_quick_switcher()
