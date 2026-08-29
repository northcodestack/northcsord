from __future__ import annotations

from textual.app import ComposeResult
from textual.widgets import Static, Tree, Label
from textual.containers import Vertical, ScrollableContainer
from textual.reactive import reactive


class ServerButton(Static):
    def __init__(self, server_id: str, name: str, icon: str = "", **kwargs):
        super().__init__(**kwargs)
        self.server_id = server_id
        self.server_name = name
        display = icon if icon else name[:2].upper() if name else "?"
        self.update(display)


class ServerSidebar(ScrollableContainer):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._servers: list[dict] = []
        self._selected: str | None = None

    def compose(self) -> ComposeResult:
        yield Label("Servers", classes="sidebar-header")

    def load_servers(self, servers: list[dict]) -> None:
        self._servers = servers
        for server in servers:
            btn = ServerButton(
                server_id=server.get("id", ""),
                name=server.get("name", "Unknown"),
                icon=server.get("icon", ""),
                classes="server-button",
            )
            self.mount(btn)


class ChannelSidebar(ScrollableContainer):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._channels: list[dict] = []
        self._selected: str | None = None

    def compose(self) -> ComposeResult:
        yield Label("Channels", classes="sidebar-header")

    def load_channels(self, channels: list[dict]) -> None:
        self._channels = channels
        for channel in channels:
            channel_type = channel.get("type", 0)
            name = channel.get("name", "unknown")
            prefix = "#" if channel_type == 0 else "?" if channel_type == 2 else ""
            channel_label = Label(
                f"{prefix}{name}",
                classes="channel-item",
            )
            self.mount(channel_label)
