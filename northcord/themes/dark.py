from __future__ import annotations


class DarkTheme:
    name = "dark"
    description = "A modern dark theme optimized for extended use"

    def get_colors(self) -> dict[str, str]:
        return {
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

    def get_styles(self) -> dict[str, any]:
        return {
            "border_style": "rounded",
            "opacity": 0.95,
        }
