from __future__ import annotations


class LightTheme:
    name = "light"
    description = "A clean light theme for well-lit environments"

    def get_colors(self) -> dict[str, str]:
        return {
            "background": "#ffffff",
            "surface": "#f5f5f5",
            "primary": "#5865f2",
            "secondary": "#ed4245",
            "text": "#2c2f33",
            "text_muted": "#747f8d",
            "accent": "#9b59b6",
            "success": "#2ecc71",
            "warning": "#f39c12",
            "error": "#e74c3c",
            "border": "#dcddde",
            "input_bg": "#e3e5e8",
            "hover": "#e8e8e8",
            "selection": "#5865f2",
        }

    def get_styles(self) -> dict[str, any]:
        return {
            "border_style": "solid",
            "opacity": 1.0,
        }
