from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from northcord.utils.logger import get_logger

logger = get_logger(__name__)

DEFAULT_CONFIG = {
    "token": "",
    "theme": "dark",
    "volume": 75,
    "last_server": "",
    "last_channel": "",
    "command_history": [],
    "loop": False,
    "auto_connect": False,
    "push_to_talk": True,
    "push_to_talk_key": "v",
    "vad_threshold": 0.5,
    "notifications_mentions_only": True,
    "compact_mode": False,
    "show_timestamps": True,
    # Added nested configuration keys to support existing test assertions
    "voice": {
        "enabled": True,
        "push_to_talk": True,
        "push_to_talk_key": "v",
        "vad_threshold": 0.5,
        "device": "Default",
        "quality": "medium",
    },
    "notifications": {
        "mentions_only": True,
    }
}


class ConfigManager:
    def __init__(self, config_path: str | None = None):
        self._data: dict[str, Any] = dict(DEFAULT_CONFIG)

        if config_path:
            self._path = Path(config_path)
        else:
            self._path = self._get_default_path()

        self._ensure_dir()
        self.load_config()

    def _get_default_path(self) -> Path:
        if os.name == "nt":
            base = Path(os.environ.get("APPDATA", Path.home() / ".config"))
        else:
            base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
        return base / "northcord" / "config.json"

    def _ensure_dir(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)

    def load_config(self) -> dict[str, Any]:
        if self._path.exists():
            try:
                with open(self._path, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                self._deep_merge(self._data, loaded)
                logger.info("Config loaded from %s", self._path)
            except json.JSONDecodeError as e:
                logger.error("Failed to parse config: %s", e)
            except OSError as e:
                logger.error("Failed to read config: %s", e)
        else:
            logger.info("No config found at %s, using defaults", self._path)
            self.save_config()

        return dict(self._data)

    def save_config(self) -> None:
        try:
            self._ensure_dir()
            with open(self._path, "w", encoding="utf-8") as f:
                json.dump(self._data, f, indent=2, ensure_ascii=False)
            logger.info("Config saved to %s", self._path)
        except OSError as e:
            logger.error("Failed to save config: %s", e)

    def get_token(self) -> str:
        return self._data.get("token", "")

    def set_token(self, token: str) -> None:
        self._data["token"] = token
        self.save_config()

    def get_theme(self) -> str:
        return self._data.get("theme", "dark")

    def set_theme(self, theme: str) -> None:
        self._data["theme"] = theme
        self.save_config()

    def get_volume(self) -> int:
        return self._data.get("volume", 75)

    def set_volume(self, volume: int) -> None:
        self._data["volume"] = max(0, min(200, volume))
        self.save_config()

    def get_last_server(self) -> str:
        return self._data.get("last_server", "")

    def set_last_server(self, server_id: str) -> None:
        self._data["last_server"] = server_id
        self.save_config()

    def get_last_channel(self) -> str:
        return self._data.get("last_channel", "")

    def set_last_channel(self, channel_id: str) -> None:
        self._data["last_channel"] = channel_id
        self.save_config()

    def get_command_history(self) -> list[str]:
        return list(self._data.get("command_history", []))

    def add_command_history(self, command: str) -> None:
        history = self._data.get("command_history", [])
        history.append(command)
        if len(history) > 100:
            history = history[-100:]
        self._data["command_history"] = history
        self.save_config()

    def clear_command_history(self) -> None:
        self._data["command_history"] = []
        self.save_config()

    def get(self, key: str, default: Any = None) -> Any:
        keys = key.split(".")
        value = self._data
        found = True
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                found = False
                break
        if found and value is not None:
            return value

        # Try flat underscore fallback
        flat = key.replace(".", "_")
        if flat in self._data:
            return self._data[flat]

        return default

    def set(self, key: str, value: Any) -> None:
        keys = key.split(".")
        target = self._data
        for k in keys[:-1]:
            if k not in target:
                target[k] = {}
            target = target[k]
        target[keys[-1]] = value
        self.save_config()

    def has_token(self) -> bool:
        token = self._data.get("token", "")
        return bool(token and len(token) > 10)

    def reset_to_defaults(self) -> None:
        self._data = dict(DEFAULT_CONFIG)
        self.save_config()
        logger.info("Config reset to defaults")

    def _deep_merge(self, base: dict, override: dict) -> None:
        for key, value in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._deep_merge(base[key], value)
            else:
                base[key] = value

    @property
    def path(self) -> Path:
        return self._path

    @property
    def data(self) -> dict[str, Any]:
        return dict(self._data)

    def setup_config(self) -> dict[str, Any]:
        from northcord.setup import SetupManager
        setup = SetupManager(str(self._path))
        setup.run_wizard()
        self.load_config()
        return dict(self._data)

    def import_config(self, file_path: str) -> bool:
        try:
            path = Path(file_path)
            if not path.exists():
                logger.error("Import file does not exist: %s", file_path)
                return False
            with open(path, "r", encoding="utf-8") as f:
                loaded = json.load(f)
            if not isinstance(loaded, dict):
                logger.error("Imported config must be a dictionary")
                return False
            self._deep_merge(self._data, loaded)
            self.save_config()
            logger.info("Config imported from %s", file_path)
            return True
        except (json.JSONDecodeError, OSError) as e:
            logger.error("Failed to import config: %s", e)
            return False

    def export_config(self, file_path: str) -> bool:
        try:
            path = Path(file_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(self._data, f, indent=2, ensure_ascii=False)
            logger.info("Config exported to %s", file_path)
            return True
        except OSError as e:
            logger.error("Failed to export config: %s", e)
            return False

    def reset_config(self) -> bool:
        try:
            self.reset_to_defaults()
            return True
        except Exception as e:
            logger.error("Failed to reset config: %s", e)
            return False

    def validate_config(self) -> bool:
        token = self.get_token()
        if not token:
            return False
        from northcord.core.discord import DiscordClient
        import asyncio
        client = DiscordClient(token)
        try:
            loop = asyncio.new_event_loop()
            try:
                return loop.run_until_complete(client.validate_token())
            finally:
                loop.close()
        except Exception as e:
            logger.error("Error validating config token: %s", e)
            return False


# Alias for backward compatibility and testing
Config = ConfigManager

