from __future__ import annotations

from textual.app import ComposeResult
from textual.widgets import Static, Label
from textual.containers import Horizontal


class NorthCordHeader(Static):
    def compose(self) -> ComposeResult:
        with Horizontal(classes="header-bar"):
            yield Label("◆ NorthCord", classes="header-title")
            yield Label("Discord, reimagined for the terminal.", classes="header-subtitle")
            yield Label("", classes="header-status", id="header-status")
