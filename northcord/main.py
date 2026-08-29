from __future__ import annotations

import argparse
import asyncio
import os
import signal
import sys
import time
from pathlib import Path

try:
    import sys
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from northcord import __version__
from northcord.app import NorthCordApp
from northcord.core.discord import DiscordClient, sanitize_token
from northcord.core.gateway import GatewayClient
from northcord.core.voice import VoiceClient
from northcord.utils.config import ConfigManager
from northcord.utils.logger import get_logger, setup_logging

logger = get_logger(__name__)


def print_banner() -> None:
    banner = """
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║   ███╗   ██╗ ██████╗ ██████╗ ████████╗██╗  ██╗ ██████╗ ██████╗ ██████╗   ║
║   ████╗  ██║██╔═══██╗██╔══██╗╚══██╔══╝██║  ██║██╔════╝██╔═══██╗██╔══██╗  ║
║   ██╔██╗ ██║██║   ██║██████╔╝   ██║   ███████║██║     ██║   ██║██████╔╝  ║
║   ██║╚██╗██║██║   ██║██╔══██╗   ██║   ██╔══██║██║     ██║   ██║██╔══██╗  ║
║   ██║ ╚████║╚██████╔╝██║  ██║   ██║   ██║  ██║╚██████╗╚██████╔╝██║  ██║  ║
║   ╚═╝  ╚═══╝ ╚═════╝ ╚═╝  ╚═╝   ╚═╝   ╚═╝  ╚═╝ ╚═════╝ ╚═════╝ ╚═╝  ╚═╝  ║
║                                                              ║
║   NorthCord v{} - Discord, reimagined for the terminal.        ║
║                                                              ║
╚══════════════════════════════════════════════════════════════════╝
""".format(__version__)
    print(banner)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="northcord",
        description="Discord, reimagined for the terminal.",
    )
    parser.add_argument(
        "--token",
        type=str,
        default=None,
        help="Directly provide Discord token",
    )
    parser.add_argument(
        "--theme",
        type=str,
        default=None,
        help="Set initial theme (dark, light, midnight, solarized, monokai)",
    )
    parser.add_argument(
        "--config",
        type=str,
        default=None,
        help="Use custom config path",
    )
    parser.add_argument(
        "--log-level",
        type=str,
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Set logging level",
    )
    parser.add_argument(
        "--log-file",
        type=str,
        default=None,
        help="Log to file",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"NorthCord v{__version__}",
    )
    parser.add_argument(
        "--no-voice",
        action="store_true",
        help="Disable voice support",
    )
    parser.add_argument(
        "--auto-connect",
        action="store_true",
        help="Auto-connect to last voice channel",
    )
    parser.add_argument(
        "--setup",
        action="store_true",
        help="Run interactive setup wizard",
    )
    parser.add_argument(
        "--quick-setup",
        action="store_true",
        help="Run non-interactive quick setup",
    )
    parser.add_argument(
        "--defaults",
        action="store_true",
        help="Setup with default settings",
    )
    parser.add_argument(
        "--rich",
        action="store_true",
        help="Run setup wizard with rich terminal styling",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Reset configuration to defaults",
    )
    parser.add_argument(
        "--export-config",
        type=str,
        default=None,
        help="Export current configuration to JSON file",
    )
    parser.add_argument(
        "--import-config",
        type=str,
        default=None,
        help="Import configuration from JSON file",
    )
    parser.add_argument(
        "--volume",
        type=int,
        default=None,
        help="Default volume value for quick setup",
    )
    return parser.parse_args()


def print_step(step: str, status: str = "...") -> None:
    print(f"  {step:<45s} {status}")


async def startup_sequence(args: argparse.Namespace) -> tuple[
    ConfigManager,
    DiscordClient,
    GatewayClient,
    VoiceClient | None,
]:
    config = ConfigManager(args.config)

    if args.token:
        config.set_token(args.token)

    raw_token = config.get_token()
    token = sanitize_token(raw_token) or ""

    if not token or len(token) < 10 or token.startswith("test_"):
        from northcord.setup import SetupManager
        setup = SetupManager(args.config)
        success = setup.run_wizard()
        if not success:
            sys.exit(1)
        config.load_config()
        raw_token = config.get_token()
        token = sanitize_token(raw_token) or ""

    discord = DiscordClient(token)
    valid = await discord.validate_token()

    if not valid:
        os.system('cls' if os.name == 'nt' else 'clear')
        from northcord.setup import SetupManager
        setup = SetupManager(args.config)
        success = setup.run_wizard()
        if success:
            print("\n  Configuration completed. Please restart NorthCord.")
        sys.exit(0)

    # Fetch user info quietly
    user_info = await discord.get_user() or {}
    username = user_info.get("username", "unknown")
    discrim = user_info.get("discriminator", "")
    display = f"{username}#{discrim}" if discrim and discrim != "0" else username

    # Fetch guilds quietly
    guilds = await discord.get_guilds()
    guild_count = len(guilds)

    # Fetch relationships (friends) quietly
    friend_count = "N/A"
    try:
        rel = await discord._request("GET", "/users/@me/relationships")
        if isinstance(rel, list):
            friends = [r for r in rel if r.get("type") == 1]
            friend_count = len(friends)
    except Exception:
        pass

    gateway = GatewayClient(token, on_event=None)

    voice_enabled = not args.no_voice and config.get("voice.enabled", True)
    voice = None
    if voice_enabled:
        voice = VoiceClient(token, "", "")

    # Clear screen and print the beautiful centered login card
    os.system('cls' if os.name == 'nt' else 'clear')
    
    width = 80
    C_PURPLE = "\033[38;2;155;89;182m"
    C_GREEN = "\033[38;2;46;204;113m"
    C_RESET = "\033[0m"
    C_GRAY = "\033[38;2;149;165;166m"
    
    banner = f"""
{C_PURPLE}╔══════════════════════════════════════════════════════╗
║                      NORTHCORD                       ║
╚══════════════════════════════════════════════════════╝{C_RESET}"""
    
    for line in banner.strip().split("\n"):
        print(line.center(width))
        
    print()
    
    line1 = f"Logged in as {C_GREEN}{display}{C_RESET}"
    line2 = f"You are currently in {C_GREEN}{guild_count}{C_RESET} server(s)."
    line3 = f"You have {C_GREEN}{friend_count}{C_RESET} Friend(s) in friend list."
    line4 = f"NorthCord's log level is {C_GREEN}{args.log_level}{C_RESET}, for command-list type /help."
    
    def print_centered_ansi(text_with_ansi: str, raw_len: int) -> None:
        spaces = max(0, (width - raw_len) // 2)
        print(" " * spaces + text_with_ansi)
        
    print_centered_ansi(line1, len(f"Logged in as {display}"))
    print_centered_ansi(line2, len(f"You are currently in {guild_count} server(s)."))
    print_centered_ansi(line3, len(f"You have {friend_count} Friend(s) in friend list."))
    print_centered_ansi(line4, len(f"NorthCord's log level is {args.log_level}, for command-list type /help."))
    
    print()
    
    v_status = f"{C_GREEN}enabled{C_RESET}" if voice_enabled else f"{C_GRAY}disabled{C_RESET}"
    g_status = f"{C_GREEN}enabled{C_RESET}"
    
    line5 = f"[!] Voice Client is {v_status}."
    line6 = f"[!] Gateway Client is {g_status}."
    
    print_centered_ansi(line5, len(f"[!] Voice Client is {'enabled' if voice_enabled else 'disabled'}."))
    print_centered_ansi(line6, len(f"[!] Gateway Client is {'enabled'}."))
    print()

    await asyncio.sleep(1.5)
    return config, discord, gateway, voice


def run_tui(config: ConfigManager, discord: DiscordClient, gateway: GatewayClient, voice: VoiceClient | None) -> None:
    print_step("Launching TUI")
    print()
    print("╚" + "═" * 60 + "╝")
    print()

    app = NorthCordApp(
        config=config,
        discord=discord,
        gateway=gateway,
        voice=voice,
    )
    app.run()


def main() -> None:
    try:
        args = parse_args()

        setup_logging(level=args.log_level, log_file=args.log_file)

        # Pre-checks for configuration CLI arguments
        if args.reset:
            config = ConfigManager(args.config)
            print(f"Resetting configuration at: {config.path}")
            if config.reset_config():
                print("Configuration reset to defaults successfully.")
            else:
                print("Failed to reset configuration.")
            sys.exit(0)

        if args.export_config:
            config = ConfigManager(args.config)
            print(f"Exporting configuration to: {args.export_config}")
            if config.export_config(args.export_config):
                print("Configuration exported successfully.")
            else:
                print("Failed to export configuration.")
                sys.exit(1)
            sys.exit(0)

        if args.import_config:
            config = ConfigManager(args.config)
            print(f"Importing configuration from: {args.import_config}")
            if config.import_config(args.import_config):
                print("Configuration imported successfully.")
            else:
                print("Failed to import configuration.")
                sys.exit(1)
            sys.exit(0)

        if args.setup or args.quick_setup:
            from northcord.setup import SetupManager
            setup = SetupManager(
                config_path=args.config,
                token=args.token,
                theme=args.theme,
                volume=args.volume,
                defaults=args.defaults,
                rich_mode=args.rich,
                quick=args.quick_setup
            )
            success = setup.run_wizard()
            if not success:
                print("Setup wizard did not complete successfully.")
                sys.exit(1)
            sys.exit(0)

        # First run check
        config_path = args.config
        if not config_path:
            if os.name == "nt":
                base = Path(os.environ.get("APPDATA", Path.home() / ".config"))
            else:
                base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
            config_file_path = base / "northcord" / "config.json"
        else:
            config_file_path = Path(config_path)

        if not config_file_path.exists():
            print("First time running NorthCord!")
            print("Starting setup wizard...")
            from northcord.setup import SetupManager
            setup = SetupManager(
                config_path=args.config,
                rich_mode=args.rich
            )
            success = setup.run_wizard()
            if not success:
                print("Initial setup cancelled or failed.")
                sys.exit(1)

        try:
            config, discord, gateway, voice = asyncio.run(startup_sequence(args))
            run_tui(config, discord, gateway, voice)

        except KeyboardInterrupt:
            print()
            logger.info("Shutdown requested")
            print("  Shutting down NorthCord...")

        except Exception as e:
            logger.error("Fatal error: %s", e)
            print(f"  Fatal error: {e}")
            sys.exit(1)
    except KeyboardInterrupt:
        os.system('cls' if os.name == 'nt' else 'clear')
        sys.exit(0)


if __name__ == "__main__":
    main()
