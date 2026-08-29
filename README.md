# NorthCord

> Discord, reimagined for the terminal.

NorthCord is a feature-rich terminal-based Discord client built with Python and Textual. Experience Discord directly from your terminal with a beautiful TUI that supports messaging, voice channels, file uploads, and full theme customization.

## Features

- **Full Messaging**: Send and receive messages with real-time updates via WebSocket gateway
- **Server & Channel Navigation**: Browse servers, channels, threads, and direct messages
- **Rich Message Rendering**: Embeds, reactions, attachments, inline images (ASCII art fallback), mentions, and markdown
- **Voice Support**: Join voice channels with push-to-talk and voice activity detection
- **File Uploads**: Drag-and-drop files to upload with progress indicators
- **Theme System**: Built-in dark/light themes with full custom theme support
- **Command System**: Slash commands, custom aliases, and built-in utility commands
- **Mentions & Notifications**: Desktop notifications for mentions and unread indicators
- **Multiple Accounts**: Single token login with secure credential storage
- **Keyboard-Driven**: Fully navigable with keyboard shortcuts, Vim-like keybinds available
- **Responsive Layout**: Adapts to terminal size with resizable panels

## Installation

### Prerequisites

- Python 3.10 or higher
- pip (Python package manager)

### Install from PyPI

```bash
pip install northcord
```

### Install from Source

```bash
git clone https://github.com/yourusername/northcord.git
cd northcord
pip install -e .
```

### Voice Dependencies (Optional)

For voice chat support, ensure you have the following system dependencies:

**Ubuntu/Debian:**
```bash
sudo apt install libopus0 portaudio19-dev
```

**macOS:**
```bash
brew install opus portaudio
```

**Windows:**
Opus and PortAudio are bundled with the Python packages.

## Usage

### Launch NorthCord

```bash
northcord
```

### First-Time Setup

1. Launch NorthCord — you'll be greeted with a welcome screen
2. Enter your Discord token (instructions at [Discord Developer Portal](https://discord.com/developers/applications))
3. Select a theme preference
4. Start chatting!

### Configuration

Configuration is stored at `~/.config/northcord/config.json`. Key settings:

```json
{
  "token": "your_discord_token_here",
  "theme": "dark",
  "keybindings": "default",
  "voice": {
    "input_device": "default",
    "output_device": "default",
    "push_to_talk": true,
    "push_to_talk_key": "v",
    "vad_threshold": 0.5
  },
  "notifications": {
    "mentions_only": true,
    "show_preview": true
  }
}
```

## Keybindings

| Key | Action |
|-----|--------|
| `Ctrl+C` | Quit |
| `Ctrl+N` | New DM |
| `Ctrl+K` | Quick switcher |
| `Ctrl+R` | Reply to message |
| `Ctrl+E` | Edit message |
| `Ctrl+U` | Upload file |
| `Ctrl+F` | Search messages |
| `Ctrl+P` | Toggle pin sidebar |
| `Ctrl+I` | Toggle member list |
| `Tab` | Next pane |
| `Shift+Tab` | Previous pane |
| `Escape` | Close panel / Cancel |
| `Up/Down` | Navigate messages |
| `Enter` | Send message / Select |
| `/` | Focus input (in channel) |
| `:`` | Command mode |

## Commands

| Command | Description |
|---------|-------------|
| `/help` | Show help screen |
| `/theme <name>` | Switch theme (dark/light/custom) |
| `/status <type>` | Set status (online/idle/dnd/invisible) |
| `/nick <name>` | Change nickname in current server |
| `/clear` | Clear current channel messages |
| `/toggle <setting>` | Toggle a setting (vad, ptt, notifications) |
| `/upload <path>` | Upload a file |
| `/join <invite>` | Join a server via invite code |
| `/quit` | Quit NorthCord |

## Themes

NorthCord ships with two built-in themes:

### Dark (Default)

A modern dark theme optimized for extended use in low-light environments.

### Light

A clean light theme for well-lit environments.

### Custom Themes

Create your own theme by placing a JSON file in `~/.config/northcord/themes/`:

```json
{
  "name": "my-theme",
  "description": "My custom theme",
  "colors": {
    "background": "#1a1a2e",
    "surface": "#16213e",
    "primary": "#0f3460",
    "secondary": "#e94560",
    "text": "#ffffff",
    "text_muted": "#a0a0b0",
    "accent": "#533483",
    "success": "#2ecc71",
    "warning": "#f39c12",
    "error": "#e74c3c",
    "border": "#2a2a4e"
  },
  "styles": {
    "border_style": "rounded",
    "opacity": 0.95
  }
}
```

Select your custom theme with `/theme my-theme`.

## Project Structure

```
northcord/
├── northcord/          # Main package
│   ├── main.py         # Entry point
│   ├── app.py          # Application class
│   ├── screens/        # TUI screens
│   ├── core/           # Discord API, gateway, voice
│   ├── themes/         # Color themes
│   ├── widgets/        # Reusable UI widgets
│   └── utils/          # Helpers, logging, config
├── data/               # Application data
├── tests/              # Test suite
└── setup.py            # Package configuration
```

## Development

```bash
# Clone the repository
git clone https://github.com/yourusername/northcord.git
cd northcord

# Install in development mode
pip install -e .

# Run tests
pytest tests/

# Lint
ruff check northcord/
```

## License

MIT License — see [LICENSE](LICENSE) for details.

## Contributing

Contributions are welcome! Please see our [Contributing Guidelines](CONTRIBUTING.md).

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## Acknowledgments

- [Textual](https://github.com/Textualize/textual) — The amazing TUI framework
- [Discord](https://discord.com) — For the API and platform
- All contributors and users
