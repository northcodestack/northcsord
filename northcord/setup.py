from __future__ import annotations

import asyncio
import getpass
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from northcord.core.discord import DiscordClient
from northcord.themes import ThemeManager
from northcord.utils.config import ConfigManager
from northcord.utils.logger import get_logger

logger = get_logger(__name__)


# Override print to be safe on environments (like CP1252/Windows) that don't support UTF-8 by default
def print(*args, **kwargs):
    import sys
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    try:
        import builtins
        builtins.print(*args, **kwargs)
    except UnicodeEncodeError:
        new_args = []
        encoding = getattr(sys.stdout, 'encoding', 'ascii') or 'ascii'
        for arg in args:
            if isinstance(arg, str):
                new_args.append(arg.encode(encoding, errors='replace').decode(encoding))
            else:
                new_args.append(arg)
        try:
            import builtins
            builtins.print(*new_args, **kwargs)
        except Exception:
            pass


class SetupManager:
    def __init__(
        self,
        config_path: str | None = None,
        token: str | None = None,
        theme: str | None = None,
        volume: int | None = None,
        defaults: bool = False,
        rich_mode: bool = False,
        quick: bool = False,
    ):
        self.config_manager = ConfigManager(config_path)
        self.token = token
        self.theme = theme
        self.volume = volume
        self.defaults = defaults
        self.rich_mode = rich_mode
        self.quick = quick
        self.total_steps = 6

        # Terminal color codes
        self.C_RESET = "\033[0m"
        self.C_BOLD = "\033[1m"
        self.C_DIM = "\033[2m"
        self.C_GREEN = "\033[38;2;46;204;113m"  # #2ecc71
        self.C_RED = "\033[38;2;231;76;60m"    # #e74c3c
        self.C_YELLOW = "\033[38;2;241;196;15m" # #f1c40f
        self.C_BLUE = "\033[38;2;52;152;219m"   # #3498db
        self.C_PURPLE = "\033[38;2;155;89;182m" # #9b59b6
        self.C_CYAN = "\033[38;2;26;188;156m"   # #1abc9c
        self.C_GRAY = "\033[38;2;149;165;166m"   # #95a5a6

    def _run_async(self, coro: Any) -> Any:
        """Helper to run async functions synchronously."""
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        if loop.is_running():
            import nest_asyncio
            nest_asyncio.apply()
            return loop.run_until_complete(coro)
        else:
            return loop.run_until_complete(coro)

    def _hex_to_rgb(self, hex_str: str) -> tuple[int, int, int]:
        hex_str = hex_str.lstrip("#")
        if len(hex_str) == 6:
            return int(hex_str[0:2], 16), int(hex_str[2:4], 16), int(hex_str[4:6], 16)
        return 255, 255, 255

    def _get_ansi_color_block(self, hex_str: str) -> str:
        r, g, b = self._hex_to_rgb(hex_str)
        return f"\033[48;2;{r};{g};{b}m  {self.C_RESET}"

    def _get_ansi_text(self, text: str, hex_str: str) -> str:
        r, g, b = self._hex_to_rgb(hex_str)
        return f"\033[38;2;{r};{g};{b}m{text}{self.C_RESET}"

    def _print_banner(self) -> None:
        banner = f"""{self.C_PURPLE}╔══════════════════════════════════════════════════════╗
║                NorthCord Setup Wizard                ║
╚══════════════════════════════════════════════════════╝{self.C_RESET}"""
        print(banner)

    def _render_screen(self, step_title: str, step_num: int, instructions: list[str], logs: list[str], prompt: str) -> None:
        """Clears the terminal and renders a clean split-layout:
           - Top 40%: Wizard banner, Step Header, and Instructions.
           - Middle 60%: Dynamic logs / status indicators.
           - Bottom: Input field.
        """
        os.system('cls' if os.name == 'nt' else 'clear')
        
        # 1. Render banner at the top
        self._print_banner()
        
        # 2. Render Step Header
        print(f"{self.C_BOLD}{self.C_CYAN}Step {step_num}/{self.total_steps}: {step_title}{self.C_RESET}")
        print(f"{self.C_DIM}{'─' * 70}{self.C_RESET}")
        
        # 3. Render Instructions (consumes max 40% area)
        for line in instructions:
            print(f"  {line}")
        print(f"{self.C_DIM}{'─' * 70}{self.C_RESET}")
        
        # 4. Render Dynamic Logs/Progress (middle area)
        print()
        for log in logs:
            print(f"  {log}")
            
        # Pad spacing up to the bottom of the screen to leave area for logs
        # Supposes standard terminal height (typically 24 lines)
        total_printed_so_far = 8 + len(instructions) + len(logs)
        pad_lines = max(1, 18 - total_printed_so_far)
        print("\n" * pad_lines, end="")
        
        # 5. Render input prompt at the bottom
        print(prompt, end="", flush=True)

    def _get_masked_input(self, prompt: str) -> str:
        """Get keyboard token input with masking."""
        try:
            import getpass
            # getpass securely hides characters during typing and pasting on all platforms natively
            val = getpass.getpass(prompt).strip()
            return val
        except KeyboardInterrupt:
            print()
            try:
                input(f"\n  {self.C_YELLOW}[!] Exit requested. Press Enter to confirm close...{self.C_RESET}")
            except (KeyboardInterrupt, Exception):
                pass
            os.system('cls' if os.name == 'nt' else 'clear')
            sys.exit(0)

    def _get_input(self, prompt: str, mask: bool = False) -> str:
        if mask:
            val = self._get_masked_input(prompt)
        else:
            try:
                val = input(prompt).strip()
            except KeyboardInterrupt:
                print()
                try:
                    input(f"\n  {self.C_YELLOW}[!] Exit requested. Press Enter to confirm close...{self.C_RESET}")
                except (KeyboardInterrupt, Exception):
                    pass
                os.system('cls' if os.name == 'nt' else 'clear')
                sys.exit(0)
        
        # Check command checks
        if val.lower() in ("/quit", "/exit", "/q", "slash bit", "slash quit"):
            os.system('cls' if os.name == 'nt' else 'clear')
            print("\n  Setup wizard exited by user command.")
            sys.exit(0)
            
        return val

    def _get_choice_from_render(self, step_title: str, step_num: int, instructions: list[str], logs: list[str], prompt: str, options: list[str]) -> str:
        """Render-aware choice selection helper."""
        full_logs = list(logs)
        full_logs.append("Available options:")
        for idx, option in enumerate(options, 1):
            full_logs.append(f"  {idx}. {option}")
        
        while True:
            self._render_screen(step_title, step_num, instructions, full_logs, prompt)
            val = self._get_input("")
            if not val and options:
                return options[0]
            try:
                choice_idx = int(val) - 1
                if 0 <= choice_idx < len(options):
                    return options[choice_idx]
            except ValueError:
                # Check case-insensitive match
                for opt in options:
                    if opt.lower().strip() == val.lower().strip():
                        return opt
            
            # If invalid, append to temp logs and redraw
            full_logs.append(f"{self.C_RED}❌ Invalid selection. Please choose 1-{len(options)}.{self.C_RESET}")

    def _get_bool_from_render(self, step_title: str, step_num: int, instructions: list[str], logs: list[str], prompt: str) -> bool:
        full_logs = list(logs)
        while True:
            self._render_screen(step_title, step_num, instructions, full_logs, prompt)
            val = self._get_input("").lower()
            if val in ("y", "yes", "true", "1", "t", "✓"):
                return True
            if val in ("n", "no", "false", "0", "f", ""):
                return False
            full_logs.append(f"{self.C_RED}❌ Invalid input. Please enter 'y' or 'n'.{self.C_RESET}")

    def _get_int_from_render(self, step_title: str, step_num: int, instructions: list[str], logs: list[str], prompt: str, min_val: int, max_val: int) -> int:
        full_logs = list(logs)
        while True:
            self._render_screen(step_title, step_num, instructions, full_logs, prompt)
            val = self._get_input("")
            if not val:
                return min_val
            try:
                int_val = int(val)
                if min_val <= int_val <= max_val:
                    return int_val
            except ValueError:
                pass
            full_logs.append(f"{self.C_RED}❌ Invalid value. Please enter an integer between {min_val} and {max_val}.{self.C_RESET}")

    def _enable_terminal_echo(self) -> None:
        """Force enable terminal echoing in case it was disabled by a crash or getpass."""
        if os.name == "nt":
            try:
                import ctypes
                kernel32 = ctypes.windll.kernel32
                hStdIn = kernel32.GetStdHandle(-10) # STD_INPUT_HANDLE
                mode = ctypes.c_uint()
                kernel32.GetConsoleMode(hStdIn, ctypes.byref(mode))
                # Enable ENABLE_ECHO_INPUT (0x0004) and ENABLE_LINE_INPUT (0x0002)
                kernel32.SetConsoleMode(hStdIn, mode.value | 0x0004 | 0x0002)
            except Exception:
                pass
        else:
            try:
                import termios
                import sys
                fd = sys.stdin.fileno()
                attrs = termios.tcgetattr(fd)
                attrs[3] = attrs[3] | termios.ECHO
                termios.tcsetattr(fd, termios.TCSADRAIN, attrs)
            except Exception:
                pass

    def run_wizard(self) -> bool:
        self._enable_terminal_echo()
        if self.quick:
            # Non-interactive quick configuration
            token = self.token or self.config_manager.get_token()
            if not token:
                logger.error("Quick setup failed: --token is required.")
                return False
            
            discord = DiscordClient(token)
            valid = self._run_async(discord.validate_token())
            if not valid:
                logger.error("Provided token is invalid.")
                return False

            theme_val = self.theme or "dark"
            volume_val = self.volume if self.volume is not None else 75

            config_data = {
                "token": token,
                "theme": theme_val,
                "volume": volume_val,
                "auto_connect": self.config_manager.get("auto_connect", False),
                "voice": {
                    "enabled": True,
                    "quality": "medium",
                },
                "log_level": "INFO",
                "debug": False,
                "message_history_limit": 1000,
            }
            self._save_config(config_data)
            return True

        if self.defaults:
            # Setup with defaults, only asking for token if not supplied
            token = self.token or self.config_manager.get_token()
            if not token:
                token = self._step_token()
            
            discord = DiscordClient(token)
            valid = self._run_async(discord.validate_token())
            if not valid:
                logger.error("Token verification failed.")
                return False

            config_data = {
                "token": token,
                "theme": "dark",
                "volume": 75,
                "auto_connect": False,
                "voice": {
                    "enabled": True,
                    "quality": "medium",
                },
                "log_level": "INFO",
                "debug": False,
                "message_history_limit": 1000,
            }
            self._save_config(config_data)
            return True

        # Interactive setup steps
        os.system('cls' if os.name == 'nt' else 'clear')
        current_step = 1
        
        # Step 1: Token Setup
        token = ""
        while not token:
            try:
                token = self._step_token()
            except Exception as e:
                choice = self._handle_error(e, "Token Setup")
                if choice == "3":
                    os.system('cls' if os.name == 'nt' else 'clear')
                    return False
                elif choice == "2":
                    token = self.config_manager.get_token()
                    if not token:
                        token = ""

        # Step 2: Verification
        current_step += 1
        user_info = {}
        try:
            user_info = self._step_verify(token)
        except Exception as e:
            # Check if user wants to bypass
            instructions = ["Verifying account details retrieved from Discord API"]
            prompt = "Verification failed. Continue setup anyway? (y/n) [y]: "
            bypass = self._get_bool_from_render("Account Verification", current_step, instructions, [f"Error: {e}"], prompt)
            if not bypass:
                os.system('cls' if os.name == 'nt' else 'clear')
                return False

        # Step 3: Appearance
        current_step += 1
        selected_theme = "dark"
        try:
            selected_theme = self._step_theme()
        except Exception:
            pass

        # Step 4: Voice settings
        current_step += 1
        voice_settings = {}
        try:
            voice_settings = self._step_voice()
        except Exception:
            voice_settings = {"volume": 75, "auto_connect": False, "auto_play": False, "quality": "medium"}

        # Step 5: Advanced settings
        current_step += 1
        advanced_settings = {}
        try:
            advanced_settings = self._step_advanced()
        except Exception:
            advanced_settings = {"log_level": "INFO", "debug": False, "message_history": 1000, "command_history": 100}

        # Step 6: Summary
        current_step += 1
        final_config = {
            "token": token,
            "theme": selected_theme,
            "volume": voice_settings.get("volume", 75),
            "auto_connect": voice_settings.get("auto_connect", False),
            "auto_play_sound": voice_settings.get("auto_play", False),
            "voice": {
                "enabled": True,
                "device": voice_settings.get("device", "Default"),
                "quality": voice_settings.get("quality", "medium"),
            },
            "log_level": advanced_settings.get("log_level", "INFO"),
            "debug": advanced_settings.get("debug", False),
            "message_history_limit": advanced_settings.get("message_history", 1000),
            "command_history_limit": advanced_settings.get("command_history", 100),
        }

        success = self._step_summary(final_config)
        return success

    def _get_northcord_info(self) -> list[str]:
        C_PURPLE = "\033[38;2;155;89;182m"
        C_CYAN = "\033[38;2;26;188;156m"
        C_RESET = "\033[0m"
        C_GRAY = "\033[38;2;149;165;166m"
        C_GREEN = "\033[38;2;46;204;113m"
        
        info = [
            f"{self.C_BOLD}About NorthCord:{self.C_RESET}",
            f"  {C_GRAY}NorthCord is a modern, lightweight, keyboard-driven Discord client{self.C_RESET}",
            f"  {C_GRAY}designed specifically for speed and utility inside the terminal.{self.C_RESET}",
            "",
            f"  {self.C_BOLD}Key Features:{self.C_RESET}",
            f"    {C_CYAN}•{self.C_RESET} {C_GREEN}Voice Channels{self.C_RESET} {C_GRAY}- High-performance audio connection and streaming.{self.C_RESET}",
            f"    {C_CYAN}•{self.C_RESET} {C_GREEN}Custom Themes{self.C_RESET}  {C_GRAY}- Complete UI theme support with 24-bit TrueColor previews.{self.C_RESET}",
            f"    {C_CYAN}•{self.C_RESET} {C_GREEN}Power Features{self.C_RESET} {C_GRAY}- Interactive message history, logging detail levels, and search.{self.C_RESET}",
            "",
            f"  {C_GRAY}Type {C_PURPLE}/quit{C_GRAY} or {C_PURPLE}/exit{C_GRAY} at any time to exit the setup wizard.{self.C_RESET}"
        ]
        return info

    def _step_token(self) -> str:
        instructions = [
            "Get Token: DevTools (F12) -> Network -> /api/v9/users/@me -> Authorization header"
        ]
        logs = []
        logs.extend(self._get_northcord_info())
        logs.append("")

        token = ""
        while not token:
            prompt = "Enter your Discord User Token: "
            self._render_screen("Token Setup", 1, instructions, logs, prompt)
            token = self._get_input("", mask=False)
            if not token:
                logs.append(f"{self.C_RED}Token cannot be empty. Please enter a valid token.{self.C_RESET}")
                continue

            logs.append("Validating token...")
            self._render_screen("Token Setup", 1, instructions, logs, "")

            discord = DiscordClient(token)
            valid = self._run_async(discord.validate_token())
            if valid:
                logs[-1] = f"Validating token... {self.C_GREEN}Done{self.C_RESET}"
                logs.append(f"Token Valid! {self.C_GREEN}✅{self.C_RESET}")
                self._render_screen("Token Setup", 1, instructions, logs, "")
                time.sleep(1.0)
                return token
            else:
                logs[-1] = f"Validating token... {self.C_RED}Failed{self.C_RESET}"
                error_reason = f" ({discord.last_error})" if discord.last_error else ""
                logs.append(f"Invalid token. Validation failed{error_reason}. {self.C_RED}❌{self.C_RESET}")
                token = ""
        return token

    def _step_verify(self, token: str) -> dict[str, Any]:
        instructions = ["Verifying account details retrieved from Discord API"]
        logs = ["Connecting to Discord..."]
        self._render_screen("Account Verification", 2, instructions, logs, "")

        discord = DiscordClient(token)
        user_info = self._run_async(discord.get_user())
        if not user_info:
            raise ConnectionError("Could not retrieve user info from Discord.")

        logs[-1] = f"Connecting to Discord... {self.C_GREEN}Done{self.C_RESET}"
        
        # Calculate snowflake date
        snowflake = int(user_info.get("id", 0))
        created_timestamp = ((snowflake >> 22) + 1420070400000) / 1000.0
        created_date = datetime.fromtimestamp(created_timestamp, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

        guilds = self._run_async(discord.get_guilds()) or []
        guild_count = len(guilds)

        friend_count = "N/A"
        try:
            rel = self._run_async(discord._request("GET", "/users/@me/relationships"))
            if isinstance(rel, list):
                friends = [r for r in rel if r.get("type") == 1]
                friend_count = str(len(friends))
        except Exception:
            pass

        username = user_info.get("username", "Unknown")
        discrim = user_info.get("discriminator", "0000")
        tag = f"{username}#{discrim}" if discrim != "0" else username
        email = user_info.get("email") or "N/A"
        user_id = user_info.get("id", "Unknown")

        # Set user logs
        logs.append(f"  Connected as: {self.C_BOLD}{tag}{self.C_RESET}")
        logs.append(f"  Email: {email}")
        logs.append(f"  User ID: {user_id}")
        logs.append(f"  Account Created: {created_date}")
        logs.append(f"  Servers: {guild_count}")
        logs.append(f"  Friends: {friend_count}")

        self._render_screen("Account Verification", 2, instructions, logs, "")
        time.sleep(2.0)
        return user_info

    def _step_theme(self) -> str:
        instructions = ["Select your preferred terminal theme colors"]
        logs = []

        manager = ThemeManager()
        themes = manager.get_available_themes()
        theme_names = [t["display"] for t in themes]
        theme_map = {t["display"]: t["name"] for t in themes}

        selected_display = self._get_choice_from_render(
            "Appearance Settings", 3, instructions, logs, "Choose theme [1]: ", theme_names
        )
        selected_name = theme_map[selected_display]

        theme_dict = manager.get_theme(selected_name)
        if theme_dict:
            colors = theme_dict.get("colors", {})
            
            # Build theme preview log blocks
            blocks = []
            for col_name in ["background", "surface", "primary", "secondary", "text", "accent", "success", "error", "warning"]:
                c_val = colors.get(col_name)
                if c_val:
                    blocks.append(self._get_ansi_color_block(c_val))
            
            logs.append(f"Theme Preview: {self.C_BOLD}{selected_display}{self.C_RESET}")
            logs.append("  Palette: " + " ".join(blocks))

            # Display preview mockup box
            bg = colors.get("background", "#313338")
            text = colors.get("text", "#dbdee1")
            accent = colors.get("accent", "#9b59b6")
            success = colors.get("success", "#3ba55d")
            error = colors.get("error", "#ed4245")
            
            logs.append(self._get_ansi_text("  ┌────────────────────────────────────────┐", bg))
            logs.append(self._get_ansi_text("  │ ", bg) + self._get_ansi_text("# general-channel", accent) + self._get_ansi_text("                      │", bg))
            logs.append(self._get_ansi_text("  │ ", bg) + self._get_ansi_text("User: Hello terminal Discord!", text) + self._get_ansi_text("        │", bg))
            logs.append(self._get_ansi_text("  │ ", bg) + self._get_ansi_text("System: ", text) + self._get_ansi_text("Connection successful! ✅", success) + self._get_ansi_text("       │", bg))
            logs.append(self._get_ansi_text("  │ ", bg) + self._get_ansi_text("Warning: ", text) + self._get_ansi_text("Error code: 404 ❌", error) + self._get_ansi_text("            │", bg))
            logs.append(self._get_ansi_text("  └────────────────────────────────────────┘", bg))

        logs.append(f"{self.C_GREEN}Theme set to: {selected_display}{self.C_RESET}")
        self._render_screen("Appearance Settings", 3, instructions, logs, "")
        time.sleep(1.5)
        return selected_name

    def _step_voice(self) -> dict[str, Any]:
        instructions = ["Configure microphone defaults and audio playback quality settings"]
        logs = []

        # Get Volume
        volume = self._get_int_from_render("Voice Settings", 4, instructions, logs, "Default Volume % [75]: ", 0, 100)
        filled = int(volume / 8.3)
        slider = "█" * filled + "░" * (12 - filled)
        logs.append(f"Volume: [{self.C_GREEN}{slider}{self.C_RESET}] {volume}%")

        # Auto-connect toggles
        auto_connect = self._get_bool_from_render("Voice Settings", 4, instructions, logs, "Auto-connect to VC? (y/n) [n]: ")
        logs.append(f"Auto-connect: {self.C_GREEN if auto_connect else self.C_GRAY}{'Enabled' if auto_connect else 'Disabled'}{self.C_RESET}")

        auto_play = self._get_bool_from_render("Voice Settings", 4, instructions, logs, "Auto-play sound on join? (y/n) [n]: ")
        logs.append(f"Auto-play join sound: {self.C_GREEN if auto_play else self.C_GRAY}{'Enabled' if auto_play else 'Disabled'}{self.C_RESET}")

        # List audio devices
        devices = ["Default Input/Output"]
        try:
            import pyaudio
            p = pyaudio.PyAudio()
            for i in range(p.get_device_count()):
                dev = p.get_device_info_by_index(i)
                if dev.get("maxInputChannels", 0) > 0 or dev.get("maxOutputChannels", 0) > 0:
                    name = dev.get("name")
                    if name and name not in devices:
                        devices.append(name)
            p.terminate()
        except Exception:
            pass

        selected_device = self._get_choice_from_render(
            "Voice Settings", 4, instructions, logs, "Choose Audio Device [1]: ", devices
        )
        logs.append(f"Device: {self.C_YELLOW}{selected_device}{self.C_RESET}")

        # Voice Audio Quality
        quality_options = ["Medium (64 kbps - Recommended)", "High (96 kbps)", "Low (32 kbps)"]
        quality_selection = self._get_choice_from_render(
            "Voice Settings", 4, instructions, logs, "Choose Voice Quality [1]: ", quality_options
        )
        quality = "medium"
        if "High" in quality_selection:
            quality = "high"
        elif "Low" in quality_selection:
            quality = "low"
        logs.append(f"Quality: {self.C_GREEN}{quality.upper()}{self.C_RESET}")

        self._render_screen("Voice Settings", 4, instructions, logs, "")
        time.sleep(1.5)
        return {
            "volume": volume,
            "auto_connect": auto_connect,
            "auto_play": auto_play,
            "device": selected_device,
            "quality": quality,
        }

    def _step_advanced(self) -> dict[str, Any]:
        instructions = ["Customize logging, debug features, and buffer limits"]
        logs = []

        log_level = self._get_choice_from_render(
            "Advanced Settings", 5, instructions, logs, "Choose Log Level [2]: ", ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        )
        logs.append(f"Log Level: {self.C_GREEN}{log_level}{self.C_RESET}")

        debug = self._get_bool_from_render("Advanced Settings", 5, instructions, logs, "Enable Debug Mode? (y/n) [n]: ")
        logs.append(f"Debug Mode: {'Enabled' if debug else 'Disabled'}")

        auto_save = self._get_bool_from_render("Advanced Settings", 5, instructions, logs, "Auto-save chat messages? (y/n) [y]: ")
        logs.append(f"Auto-save chat: {'Enabled' if auto_save else 'Disabled'}")

        msg_limit = self._get_int_from_render("Advanced Settings", 5, instructions, logs, "Message History Limit [1000]: ", 10, 10000)
        logs.append(f"Message Limit: {msg_limit}")

        cmd_limit = self._get_int_from_render("Advanced Settings", 5, instructions, logs, "Command History Limit [100]: ", 10, 1000)
        logs.append(f"Command Limit: {cmd_limit}")

        auto_update = self._get_bool_from_render("Advanced Settings", 5, instructions, logs, "Auto-check for updates? (y/n) [y]: ")
        logs.append(f"Auto-update checks: {'Enabled' if auto_update else 'Disabled'}")

        self._render_screen("Advanced Settings", 5, instructions, logs, "")
        time.sleep(1.5)
        return {
            "log_level": log_level,
            "debug": debug,
            "auto_save": auto_save,
            "message_history": msg_limit,
            "command_history": cmd_limit,
            "auto_update": auto_update,
        }

    def _step_summary(self, config: dict[str, Any]) -> bool:
        instructions = ["Review configurations and finalize setup"]
        logs = []

        token_masked = "Valid (Masked)" if config.get("token") else "Not configured"
        theme_disp = config.get("theme", "dark").capitalize()
        volume = config.get("volume", 75)
        auto_connect = "Enabled" if config.get("auto_connect") else "Disabled"
        log_level = config.get("log_level", "INFO")
        debug = "Enabled" if config.get("debug") else "Disabled"

        summary_box = f"""
{self.C_GRAY}  ┌─────────────────────────────────────────────────────────────────────┐
  │  Token:          {self.C_GREEN}✅ {token_masked:<48s}{self.C_GRAY} │
  │  Theme:          {theme_disp:<51s} │
  │  Volume:         {volume:<51d} │
  │  Auto-Connect:   {auto_connect:<51s} │
  │  Log Level:      {log_level:<51s} │
  │  Debug Mode:     {debug:<51s} │
  └─────────────────────────────────────────────────────────────────────┘{self.C_RESET}
"""
        for line in summary_box.strip("\n").split("\n"):
            logs.append(line)

        options = [
            "💾 Save Configuration",
            "▶️ Launch NorthCord",
            "❌ Cancel and Exit"
        ]
        
        choice = self._get_choice_from_render(
            "Summary & Complete", 6, instructions, logs, "Select Option [1]: ", options
        )

        if "Save" in choice:
            self._save_config(config)
            logs.append(f"{self.C_GREEN}Configuration saved successfully!{self.C_RESET}")
            self._render_screen("Summary & Complete", 6, instructions, logs, "")
            time.sleep(2.0)
            os.system('cls' if os.name == 'nt' else 'clear')
            return True
        elif "Launch" in choice:
            self._save_config(config)
            logs.append(f"{self.C_GREEN}Configuration saved. Initializing launch...{self.C_RESET}")
            self._render_screen("Summary & Complete", 6, instructions, logs, "")
            time.sleep(1.0)
            os.system('cls' if os.name == 'nt' else 'clear')
            return True
        else:
            logs.append(f"{self.C_YELLOW}Configuration wizard cancelled.{self.C_RESET}")
            self._render_screen("Summary & Complete", 6, instructions, logs, "")
            time.sleep(1.5)
            os.system('cls' if os.name == 'nt' else 'clear')
            return False

    def _save_config(self, config: dict[str, Any]) -> None:
        data = self.config_manager.data
        data.update(config)
        self.config_manager._data = data
        self.config_manager.save_config()

    def _handle_error(self, error: Exception, step: str) -> str:
        instructions = [f"An error occurred in {step}"]
        logs = [f"{self.C_RED}❌ Error details: {error}{self.C_RESET}"]
        options = [
            "Retry this step",
            "Skip this step (use defaults/existing)",
            "Exit setup"
        ]
        return self._get_choice_from_render(
            "Error Recovery", 0, instructions, logs, "Choose Option [1]: ", options
        )
