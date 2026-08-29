from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import Header, Footer, Static, Markdown
from textual.containers import Vertical, ScrollableContainer


HELP_CONTENT = """# NorthCord Help

## Keybindings

| Key | Action |
|-----|--------|
| `Ctrl+C` | Quit |
| `Ctrl+K` | Quick Switcher |
| `Ctrl+S` | Settings |
| `Ctrl+H` | Help |
| `Tab` | Next Pane |
| `Shift+Tab` | Previous Pane |
| `/` | Focus Input |
| `Escape` | Back / Cancel |

## Commands

| Command | Description |
|---------|-------------|
| `/help` | Show this help screen |
| `/theme <name>` | Switch theme |
| `/status <type>` | Set status |
| `/nick <name>` | Change nickname |
| `/clear` | Clear chat |
| `/toggle <setting>` | Toggle setting |
| `/upload <path>` | Upload file |
| `/join <invite>` | Join server |
| `/quit` | Quit NorthCord |

## Tips

- Press `/` to quickly focus the message input
- Use `Ctrl+K` to quickly switch between servers and channels
- Configure themes, notifications, and voice in Settings (`Ctrl+S`)
"""


class HelpScreen(Screen):
    BINDINGS = [
        Binding("escape", "back", "Back"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        yield ScrollableContainer(
            Markdown(HELP_CONTENT, id="help-content"),
        )
        yield Footer()

    def action_back(self) -> None:
        self.dismiss()
