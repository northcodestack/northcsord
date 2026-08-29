from __future__ import annotations

from typing import Any

from northcord.utils.logger import get_logger

logger = get_logger(__name__)


DISCORD_DARK = {
    "name": "dark",
    "display": "Discord Dark",
    "description": "Default Discord dark theme",
    "colors": {
        "background": "#313338",
        "surface": "#2b2d31",
        "primary": "#5865f2",
        "secondary": "#ed4245",
        "text": "#dbdee1",
        "text_muted": "#949ba4",
        "accent": "#9b59b6",
        "success": "#3ba55d",
        "warning": "#faa81a",
        "error": "#ed4245",
        "border": "#1e1f22",
        "input_bg": "#1e1f22",
        "hover": "#35373c",
        "selection": "#5865f2",
        "mention": "#5865f240",
        "link": "#00a8fc",
        "header_bg": "#1e1f22",
        "sidebar_bg": "#2b2d31",
        "channel_item": "#949ba4",
        "channel_hover": "#dbdee1",
        "button_primary": "#5865f2",
        "button_danger": "#da373c",
    },
    "styles": {
        "border_style": "solid",
        "opacity": 1.0,
        "font_size": 10,
        "font_family": "monospace",
    },
}

DISCORD_LIGHT = {
    "name": "light",
    "display": "Discord Light",
    "description": "Default Discord light theme",
    "colors": {
        "background": "#ffffff",
        "surface": "#f2f3f5",
        "primary": "#5865f2",
        "secondary": "#ed4245",
        "text": "#2e3338",
        "text_muted": "#747f8d",
        "accent": "#9b59b6",
        "success": "#3ba55d",
        "warning": "#faa81a",
        "error": "#ed4245",
        "border": "#dcddde",
        "input_bg": "#e3e5e8",
        "hover": "#e8e8e8",
        "selection": "#5865f2",
        "mention": "#5865f220",
        "link": "#0068e0",
        "header_bg": "#f2f3f5",
        "sidebar_bg": "#f2f3f5",
        "channel_item": "#747f8d",
        "channel_hover": "#2e3338",
        "button_primary": "#5865f2",
        "button_danger": "#da373c",
    },
    "styles": {
        "border_style": "solid",
        "opacity": 1.0,
        "font_size": 10,
        "font_family": "monospace",
    },
}

MIDNIGHT_BLUE = {
    "name": "midnight",
    "display": "Midnight Blue",
    "description": "A dark blue theme for late-night users",
    "colors": {
        "background": "#0d1117",
        "surface": "#161b22",
        "primary": "#58a6ff",
        "secondary": "#f85149",
        "text": "#c9d1d9",
        "text_muted": "#8b949e",
        "accent": "#bc8cff",
        "success": "#3fb950",
        "warning": "#d29922",
        "error": "#f85149",
        "border": "#21262d",
        "input_bg": "#0d1117",
        "hover": "#1c2128",
        "selection": "#58a6ff",
        "mention": "#58a6ff30",
        "link": "#58a6ff",
        "header_bg": "#161b22",
        "sidebar_bg": "#0d1117",
        "channel_item": "#8b949e",
        "channel_hover": "#c9d1d9",
        "button_primary": "#238636",
        "button_danger": "#da3633",
    },
    "styles": {
        "border_style": "rounded",
        "opacity": 0.95,
        "font_size": 10,
        "font_family": "monospace",
    },
}

SOLARIZED = {
    "name": "solarized",
    "display": "Solarized",
    "description": "Solarized color scheme - low contrast",
    "colors": {
        "background": "#002b36",
        "surface": "#073642",
        "primary": "#268bd2",
        "secondary": "#dc322f",
        "text": "#839496",
        "text_muted": "#657b83",
        "accent": "#6c71c4",
        "success": "#859900",
        "warning": "#b58900",
        "error": "#dc322f",
        "border": "#073642",
        "input_bg": "#002b36",
        "hover": "#09434f",
        "selection": "#268bd2",
        "mention": "#268bd240",
        "link": "#268bd2",
        "header_bg": "#073642",
        "sidebar_bg": "#002b36",
        "channel_item": "#657b83",
        "channel_hover": "#839496",
        "button_primary": "#859900",
        "button_danger": "#dc322f",
    },
    "styles": {
        "border_style": "solid",
        "opacity": 0.92,
        "font_size": 10,
        "font_family": "monospace",
    },
}

MONOKAI = {
    "name": "monokai",
    "display": "Monokai",
    "description": "Monokai color scheme - vibrant",
    "colors": {
        "background": "#272822",
        "surface": "#2d2e27",
        "primary": "#a6e22e",
        "secondary": "#f92672",
        "text": "#f8f8f2",
        "text_muted": "#75715e",
        "accent": "#ae81ff",
        "success": "#a6e22e",
        "warning": "#e6db74",
        "error": "#f92672",
        "border": "#3e3d32",
        "input_bg": "#1e1f1c",
        "hover": "#383830",
        "selection": "#a6e22e",
        "mention": "#a6e22e30",
        "link": "#66d9ef",
        "header_bg": "#2d2e27",
        "sidebar_bg": "#272822",
        "channel_item": "#75715e",
        "channel_hover": "#f8f8f2",
        "button_primary": "#a6e22e",
        "button_danger": "#f92672",
    },
    "styles": {
        "border_style": "rounded",
        "opacity": 0.93,
        "font_size": 10,
        "font_family": "monospace",
    },
}

BUILT_IN_THEMES: dict[str, dict] = {
    "dark": DISCORD_DARK,
    "light": DISCORD_LIGHT,
    "midnight": MIDNIGHT_BLUE,
    "solarized": SOLARIZED,
    "monokai": MONOKAI,
}


class ThemeManager:
    def __init__(self):
        self._themes: dict[str, dict] = dict(BUILT_IN_THEMES)
        self._current: str = "dark"

    def get_theme(self, name: str) -> dict | None:
        theme = self._themes.get(name)
        if theme:
            return dict(theme)
        return None

    def set_theme(self, name: str) -> bool:
        if name in self._themes:
            self._current = name
            logger.info("Theme changed to '%s'", name)
            return True
        logger.warning("Theme '%s' not found", name)
        return False

    def add_custom_theme(self, name: str, theme: dict) -> None:
        self._themes[name] = theme
        logger.info("Custom theme '%s' added", name)

    def get_available_themes(self) -> list[dict[str, str]]:
        return [
            {
                "name": t["name"],
                "display": t["display"],
                "description": t["description"],
            }
            for t in self._themes.values()
        ]

    def get_current_theme(self) -> dict:
        return dict(self._themes.get(self._current, DISCORD_DARK))

    def get_current_name(self) -> str:
        return self._current

    def get_colors(self, name: str | None = None) -> dict[str, str]:
        theme = self._themes.get(name or self._current, DISCORD_DARK)
        return dict(theme.get("colors", {}))

    def get_styles(self, name: str | None = None) -> dict[str, Any]:
        theme = self._themes.get(name or self._current, DISCORD_DARK)
        return dict(theme.get("styles", {}))

    def remove_theme(self, name: str) -> bool:
        if name in BUILT_IN_THEMES:
            logger.warning("Cannot remove built-in theme '%s'", name)
            return False
        if name in self._themes:
            del self._themes[name]
            if self._current == name:
                self._current = "dark"
            return True
        return False
