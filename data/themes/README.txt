Place custom theme JSON files in this directory.

Each theme file should follow this format:
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

Use the command /theme <name> to apply a custom theme.
