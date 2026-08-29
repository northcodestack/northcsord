from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import Header, Footer, Button, Label, Select, Static
from textual.containers import Vertical, Horizontal
from textual.widgets._select import Option


class SettingsScreen(Screen):
    BINDINGS = [
        Binding("escape", "back", "Back"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        yield Vertical(
            Label("Settings", id="settings-title", classes="screen-title"),
            Horizontal(
                Label("Theme:"),
                Select(
                    [
                        Option("dark", "Dark"),
                        Option("light", "Light"),
                    ],
                    id="theme-select",
                    value=self.app.current_theme if hasattr(self.app, "current_theme") else "dark",
                ),
                id="theme-row",
            ),
            Horizontal(
                Label("Notifications:"),
                Select(
                    [
                        Option("all", "All Messages"),
                        Option("mentions", "Mentions Only"),
                        Option("none", "None"),
                    ],
                    id="notifications-select",
                    value="mentions",
                ),
                id="notifications-row",
            ),
            Horizontal(
                Label("Voice Mode:"),
                Select(
                    [
                        Option("ptt", "Push to Talk"),
                        Option("vad", "Voice Activity"),
                        Option("disabled", "Disabled"),
                    ],
                    id="voice-select",
                    value="ptt",
                ),
                id="voice-row",
            ),
            Button("Apply", id="apply-btn", variant="primary"),
            Button("Back", id="back-btn", variant="default"),
            id="settings-content",
        )
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "apply-btn":
            self.apply_settings()
        elif event.button.id == "back-btn":
            self.dismiss()

    def apply_settings(self) -> None:
        theme_select = self.query_one("#theme-select", Select)
        theme_value = theme_select.value
        if theme_value:
            self.app.apply_theme(theme_value)
            self.notify("Settings applied!", severity="information")

    def action_back(self) -> None:
        self.dismiss()
