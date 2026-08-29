from __future__ import annotations

import json
from pathlib import Path

from northcord.utils.logger import get_logger

logger = get_logger(__name__)


class CustomTheme:
    def __init__(self, theme_name: str):
        self.name = theme_name
        self.description = f"Custom theme: {theme_name}"

        self._colors: dict[str, str] = {
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
            "border": "#2a2a4e",
            "input_bg": "#0d1b2a",
            "hover": "#1b1b3a",
            "selection": "#0f3460",
        }
        self._styles: dict = {
            "border_style": "rounded",
            "opacity": 0.95,
        }

        self._load()

    def _load(self) -> None:
        theme_dir = Path.home() / ".config" / "northcord" / "themes"
        theme_file = theme_dir / f"{self.name}.json"

        if not theme_file.exists():
            logger.warning("Custom theme '%s' not found at %s, using defaults", self.name, theme_file)
            return

        try:
            with open(theme_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            if "colors" in data:
                self._colors.update(data["colors"])
            if "styles" in data:
                self._styles.update(data["styles"])
            if "name" in data:
                self.name = data["name"]
            if "description" in data:
                self.description = data["description"]

            logger.info("Loaded custom theme '%s' from %s", self.name, theme_file)
        except (json.JSONDecodeError, OSError) as e:
            logger.error("Failed to load custom theme '%s': %s", self.name, e)

    def get_colors(self) -> dict[str, str]:
        return dict(self._colors)

    def get_styles(self) -> dict:
        return dict(self._styles)
