from __future__ import annotations

import asyncio
from typing import Any

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.reactive import reactive
from textual.widgets import Header, Footer, Static, Input, Button, Label, ListView, ListItem, Select, Markdown
from textual.containers import Horizontal, Vertical, ScrollableContainer
from textual.screen import Screen
from textual.widgets._select import Option

from northcord.core.discord import DiscordClient
from northcord.core.gateway import GatewayClient
from northcord.core.voice import VoiceClient
from northcord.core.commands import CommandHandler
from northcord.themes import ThemeManager
from northcord.utils.config import ConfigManager
from northcord.utils.logger import get_logger

logger = get_logger(__name__)


class ServerList(ScrollableContainer):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._servers: list[dict] = []

    def compose(self) -> ComposeResult:
        yield Label("Servers", classes="sidebar-title")

    def load_servers(self, servers: list[dict]) -> None:
        self._servers = servers
        for server in servers:
            name = server.get("name", "Unknown")
            btn = Button(name[:2].upper(), id=f"server-{server['id']}", classes="server-btn")
            self.mount(btn)


class ChannelList(ScrollableContainer):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._channels: list[dict] = []

    def compose(self) -> ComposeResult:
        yield Label("Channels", classes="sidebar-title")

    def load_channels(self, channels: list[dict]) -> None:
        self._channels = channels
        for ch in channels:
            ch_type = ch.get("type", 0)
            name = ch.get("name", "unknown")
            prefix = "#" if ch_type == 0 else "?" if ch_type == 2 else ""
            btn = Button(f"{prefix}{name}", id=f"channel-{ch['id']}", classes="channel-btn")
            self.mount(btn)


class MessageWidget(Static):
    def __init__(self, author: str, content: str, timestamp: str = "", **kwargs):
        super().__init__(**kwargs)
        self._author = author
        self._content = content
        self._timestamp = timestamp

    def compose(self) -> ComposeResult:
        with Horizontal(classes="msg-row"):
            yield Label(self._author, classes="msg-author")
            if self._timestamp:
                yield Label(self._timestamp, classes="msg-time")
        yield Label(self._content, classes="msg-content")


class MessageListWidget(ListView):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._message_data: list[dict] = []

    def add_message(self, author: str, content: str, timestamp: str = "", message_id: str = "") -> None:
        self._message_data.append({"author": author, "content": content, "timestamp": timestamp, "id": message_id})
        item = ListItem(MessageWidget(author, content, timestamp))
        self.append(item)
        self.scroll_end(animate=False)

    def load_messages(self, messages: list[dict]) -> None:
        self.clear()
        self._message_data = []
        for msg in reversed(messages):
            author_data = msg.get("author", {})
            author = author_data.get("global_name") or author_data.get("username", "Unknown")
            content = msg.get("content", "")
            ts = msg.get("timestamp", "")
            mid = msg.get("id", "")
            self._message_data.append({"author": author, "content": content, "timestamp": ts, "id": mid})
        for m in self._message_data:
            item = ListItem(MessageWidget(m["author"], m["content"], m["timestamp"]))
            self.append(item)
        self.scroll_end(animate=False)

    def clear_messages(self) -> None:
        self.clear()
        self._message_data = []


class InputBar(Input):
    def __init__(self, **kwargs):
        super().__init__(placeholder="/ for commands, or type a message...", **kwargs)


class StatusBar(Static):
    def compose(self) -> ComposeResult:
        with Horizontal(classes="status-bar"):
            yield Label("Status: Disconnected", id="status-text")
            yield Label("Servers: 0", id="status-servers")
            yield Label("Users: 0", id="status-users")
            yield Label("VC: None", id="status-vc")


class SearchBar(Input):
    def __init__(self, **kwargs):
        super().__init__(placeholder="Search messages...", **kwargs)


class MainScreen(Screen):
    BINDINGS = [
        Binding("tab", "focus_next", "Next Pane", show=False),
        Binding("shift+tab", "focus_prev", "Prev Pane", show=False),
        Binding("/", "focus_input", "Focus Input", show=False),
        Binding("escape", "focus_sidebar", "Focus Sidebar", show=False),
    ]

    def compose(self) -> ComposeResult:
        yield Horizontal(
            Vertical(
                ServerList(id="server-list"),
                ChannelList(id="channel-list"),
                classes="sidebar-panel",
            ),
            Vertical(
                MessageListWidget(id="message-list"),
                InputBar(id="input-bar"),
                classes="main-panel",
            ),
            classes="app-layout",
        )
        yield StatusBar(id="status-bar")

    def action_focus_input(self) -> None:
        self.query_one("#input-bar", InputBar).focus()

    def action_focus_sidebar(self) -> None:
        self.query_one("#server-list", ServerList).focus()

    def action_focus_next(self) -> None:
        self.focus_next()

    def action_focus_prev(self) -> None:
        self.focus_previous()


class SettingsScreen(Screen):
    BINDINGS = [Binding("escape", "dismiss", "Back")]

    def compose(self) -> ComposeResult:
        yield Header()
        yield Vertical(
            Label("Settings", classes="screen-title"),
            Horizontal(Label("Theme:"), Select(
                [Option("dark", "Discord Dark"), Option("light", "Discord Light"),
                 Option("midnight", "Midnight Blue"), Option("solarized", "Solarized"),
                 Option("monokai", "Monokai")],
                id="theme-select", value="dark",
            )),
            Horizontal(Label("Volume:"), Input(value="75", id="volume-input", type="integer")),
            Horizontal(Label("Push to Talk:"), Select([Option("true", "Enabled"), Option("false", "Disabled")], id="ptt-select")),
            Horizontal(Label("Notifications:"), Select([Option("all", "All"), Option("mentions", "Mentions Only"), Option("none", "None")], id="notif-select")),
            Button("Apply", id="apply-btn", variant="primary"),
            Button("Back", id="back-btn"),
            classes="settings-content",
        )
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "apply-btn":
            self.app.notify("Settings applied!", severity="information")
        elif event.button.id == "back-btn":
            self.dismiss()


class HelpScreen(Screen):
    BINDINGS = [Binding("escape", "dismiss", "Back")]

    def compose(self) -> ComposeResult:
        yield Header()
        yield ScrollableContainer(
            Markdown("""# NorthCord Help

## Keybindings
| Key | Action |
|-----|--------|
| `/` | Focus input |
| `Tab` | Next pane |
| `Escape` | Back / Focus sidebar |
| `Ctrl+C` | Quit |
| `Ctrl+K` | Quick Switcher |
| `Ctrl+S` | Settings |
| `Ctrl+H` | Help |

## Commands
| Command | Description |
|---------|-------------|
| `/help [cmd]` | Show help for a command |
| `/join` | Join voice channel |
| `/leave` | Leave voice channel |
| `/play <file>` | Play audio in VC |
| `/stop` | Stop playback |
| `/volume <0-200>` | Set volume |
| `/upload <file>` | Upload file |
| `/status <text>` | Set custom status |
| `/theme <name>` | Change theme |
| `/purge <n>` | Delete n messages |
| `/profile` | View profile |
| `/search <text>` | Search messages |
| `/clear` | Clear chat |
| `/exit` | Exit NorthCord |

Type `/help <command>` for details on a specific command.
""", id="help-content"),
        )
        yield Footer()


class ProfileScreen(Screen):
    BINDINGS = [Binding("escape", "dismiss", "Back")]

    def compose(self) -> ComposeResult:
        yield Header()
        yield Vertical(
            Label("Profile", classes="screen-title"),
            Label(f"Username: {self._get_username()}"),
            Label(f"ID: {self._get_user_id()}"),
            Button("Back", id="back-btn"),
            classes="profile-content",
        )
        yield Footer()

    def _get_username(self) -> str:
        dc = getattr(self.app, "discord", None)
        if dc and dc.user:
            return dc.user.get("global_name") or dc.user.get("username", "Unknown")
        return "Not connected"

    def _get_user_id(self) -> str:
        dc = getattr(self.app, "discord", None)
        if dc and dc.user:
            return dc.user.get("id", "N/A")
        return "N/A"

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss()


class NorthCordApp(App):
    TITLE = "NorthCord"
    SUB_TITLE = "Discord, reimagined for the terminal."

    CSS = """
    Screen {
        background: $surface;
    }
    .app-layout {
        height: 100%;
    }
    .sidebar-panel {
        width: 25;
        min-width: 20;
        background: $surface;
        border-right: solid $border;
    }
    .main-panel {
        width: 1fr;
    }
    .sidebar-title {
        padding: 0 1;
        text-style: bold;
        color: $text-muted;
    }
    .server-btn {
        width: 100%;
        min-height: 2;
        content-align: center middle;
    }
    .channel-btn {
        width: 100%;
    }
    .msg-row {
        height: 1;
    }
    .msg-author {
        color: $primary;
        text-style: bold;
    }
    .msg-time {
        color: $text-muted;
        margin-left: 1;
    }
    .msg-content {
        margin-left: 1;
    }
    .status-bar {
        height: 1;
        background: $primary;
        color: $text;
    }
    .status-bar > Label {
        margin: 0 2;
    }
    #input-bar {
        dock: bottom;
        height: 3;
    }
    .screen-title {
        text-style: bold;
        height: 3;
        content-align: center middle;
    }
    .settings-content, .profile-content {
        padding: 1 2;
    }
    .settings-content > Horizontal {
        height: 3;
    }
    #help-content {
        padding: 1 2;
    }
    """

    BINDINGS = [
        Binding("ctrl+c", "quit", "Quit", priority=True),
        Binding("ctrl+k", "quick_switcher", "Quick Switcher"),
        Binding("ctrl+s", "open_settings", "Settings"),
        Binding("ctrl+h", "open_help", "Help"),
        Binding("ctrl+p", "open_profile", "Profile"),
    ]

    def __init__(
        self,
        config: ConfigManager,
        discord: DiscordClient,
        gateway: GatewayClient,
        voice: VoiceClient | None = None,
        **kwargs: Any,
    ):
        super().__init__(**kwargs)
        self.config = config
        self.discord = discord
        self.gateway = gateway
        self.voice = voice
        self.commands = CommandHandler(discord, gateway, voice)
        self.theme_manager = ThemeManager()

    def compose(self) -> ComposeResult:
        yield MainScreen()

    def on_mount(self) -> None:
        theme_name = self.config.get_theme()
        self.apply_theme(theme_name)
        self.connect_gateway()
        self.load_ui_data()

    def connect_gateway(self) -> None:
        if self.discord.token:
            loop = asyncio.get_running_loop()
            loop.create_task(self.gateway.connect())
            self._update_status("Connected")

    def load_ui_data(self) -> None:
        screen = self.query_one(MainScreen)
        server_list = screen.query_one("#server-list", ServerList)
        msg_list = screen.query_one("#message-list", MessageListWidget)
        status_bar = screen.query_one("#status-bar", StatusBar)

        guilds = self.discord.get_guilds()
        try:
            guilds_result = asyncio.run(self.discord.get_guilds()) if not isinstance(guilds, list) else guilds
        except Exception:
            guilds_result = []

        server_list.load_servers([])
        msg_list.add_message("NorthCord", "Welcome to NorthCord! Type /help to get started.")

        servers_label = status_bar.query_one("#status-servers", Label)
        try:
            servers_label.update(f"Servers: {len(guilds_result)}")
        except Exception:
            pass

    def apply_theme(self, theme_name: str) -> None:
        success = self.theme_manager.set_theme(theme_name)
        if not success:
            logger.warning("Theme '%s' not found, using dark", theme_name)
            self.theme_manager.set_theme("dark")

        colors = self.theme_manager.get_colors()
        css_vars = {}
        for key, value in colors.items():
            var_name = f"${key}"
            css_vars[var_name] = value

        self.set_css_variables(**css_vars)
        self.refresh_css()
        self.notify(f"Theme: {theme_name}", severity="information")
        logger.info("Applied theme: %s", theme_name)

    def set_css_variables(self, **variables: str) -> None:
        css = self.CSS or ""
        var_lines = []
        for key, value in variables.items():
            var_lines.append(f"  {key}: {value};")
        if var_lines:
            var_block = "Screen {\n" + "\n".join(var_lines) + "\n}\n"
            css = var_block + css
        self.CSS = css

    def _update_status(self, status: str) -> None:
        try:
            screen = self.query_one(MainScreen)
            status_bar = screen.query_one("#status-bar", StatusBar)
            status_text = status_bar.query_one("#status-text", Label)
            status_text.update(f"Status: {status}")
        except Exception:
            pass

    def handle_event(self, event_type: str, data: dict) -> None:
        if event_type == "MESSAGE_CREATE":
            screen = self.query_one(MainScreen)
            msg_list = screen.query_one("#message-list", MessageListWidget)
            author_data = data.get("author", {})
            author = author_data.get("global_name") or author_data.get("username", "Unknown")
            content = data.get("content", "")
            ts = data.get("timestamp", "")
            msg_list.add_message(author, content, ts)

    def action_open_settings(self) -> None:
        self.push_screen(SettingsScreen())

    def action_open_help(self) -> None:
        self.push_screen(HelpScreen())

    def action_open_profile(self) -> None:
        self.push_screen(ProfileScreen())

    def action_quick_switcher(self) -> None:
        self.notify("Quick Switcher (Ctrl+K)", severity="information")

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "input-bar":
            value = event.input.value.strip()
            if not value:
                return

            if value.startswith("/"):
                result = self.commands.execute(value)
                if result:
                    screen = self.query_one(MainScreen)
                    msg_list = screen.query_one("#message-list", MessageListWidget)
                    msg_list.add_message("System", result)
            else:
                asyncio.create_task(self._send_message(value))

            event.input.clear()

    async def _send_message(self, content: str) -> None:
        channel_id = self.config.get_last_channel()
        if not channel_id:
            screen = self.query_one(MainScreen)
            msg_list = screen.query_one("#message-list", MessageListWidget)
            msg_list.add_message("System", "No channel selected. Use /channel to select one.")
            return
        await self.discord.send_message(channel_id, content)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        button_id = event.button.id or ""
        if button_id.startswith("server-"):
            guild_id = button_id.replace("server-", "")
            self._select_server(guild_id)
        elif button_id.startswith("channel-"):
            channel_id = button_id.replace("channel-", "")
            self._select_channel(channel_id)

    def _select_server(self, guild_id: str) -> None:
        self.config.set_last_server(guild_id)
        channels = self.discord.get_channels(guild_id)
        try:
            channels_result = asyncio.run(self.discord.get_channels(guild_id))
            screen = self.query_one(MainScreen)
            ch_list = screen.query_one("#channel-list", ChannelList)
            ch_list.load_channels(channels_result)
        except Exception:
            pass

    def _select_channel(self, channel_id: str) -> None:
        self.config.set_last_channel(channel_id)
        try:
            messages = asyncio.run(self.discord.get_messages(channel_id, limit=50))
            screen = self.query_one(MainScreen)
            msg_list = screen.query_one("#message-list", MessageListWidget)
            msg_list.load_messages(messages)
        except Exception:
            pass

    def on_unmount(self) -> None:
        try:
            loop = asyncio.new_event_loop()
            loop.run_until_complete(self.gateway.disconnect())
            self.discord.close()
            if self.voice:
                loop.run_until_complete(self.voice.disconnect())
        except Exception:
            pass
