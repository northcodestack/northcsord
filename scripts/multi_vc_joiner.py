#!/usr/bin/env python3
import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any

# Ensure project root is in sys.path
sys.path.insert(0, "d:/Devs/GitHub/NorthCord")

from northcord.core.gateway import GatewayClient
from northcord.core.discord import DiscordClient


async def validate_token_info(token: str) -> tuple[str, bool, str]:
    """Validate a token and return (token, is_valid, username_or_error)"""
    token = token.strip().strip("'\"")
    if not token:
        return token, False, "Empty token"

    discord = DiscordClient(token)
    try:
        valid = await discord.validate_token()
        if valid:
            username = discord.user.get("username", "Unknown")
            return token, True, username
        else:
            return token, False, "Invalid token"
    except Exception as e:
        return token, False, str(e)


async def join_token(token: str, username: str, guild_id: str, channel_id: str, mute: bool, deaf: bool):
    """Run gateway connection and join VC for a validated token"""
    gateway = GatewayClient(token)
    
    # Wait for gateway ready before we send voice state update
    connected_event = asyncio.Event()
    
    def on_event(event_type: str, data: dict[str, Any]):
        if event_type == "READY":
            connected_event.set()

    gateway.on_event = on_event

    await gateway.connect()
    
    # Wait for the gateway to handshake
    try:
        await asyncio.wait_for(connected_event.wait(), timeout=10.0)
        print(f"🌐 Gateway Connected: {username}")
        # Send voice state update to join VC
        await gateway.update_voice_state(guild_id, channel_id, mute, deaf)
        print(f"✅ Joined Channel {channel_id} in Guild {guild_id}: {username}")
    except asyncio.TimeoutError:
        print(f"⚠️ Gateway handshake timeout for: {username}")
        return

    # Keep connection alive
    while gateway.is_connected:
        await asyncio.sleep(1.0)


async def main():
    # Force UTF-8 encoding for screen icons / checkmarks
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except:
        pass

    print("=" * 60)
    print("  🚀 NorthCord Multiple VC Joiner Tool")
    print("=" * 60)
    
    # Find tokens file
    token_file = Path("data/tokens.txt")
    if not token_file.exists():
        os.makedirs("data", exist_ok=True)
        # Fallback check for config token
        token_file.write_text("PASTE_YOUR_TOKENS_HERE_ONE_PER_LINE\n")
        print(f"📝 Created empty data/tokens.txt. Please paste tokens there.")
        print(f"   Or provide guild_id and channel_id below to test with config token.")
        print()

    tokens = []
    if token_file.exists():
        with open(token_file, "r", encoding="utf-8") as f:
            tokens = [line.strip() for line in f if line.strip() and not line.startswith("#") and "PASTE_YOUR_TOKENS_HERE" not in line]

    # If no tokens in data/tokens.txt, check if there's any tokens in config.json
    if not tokens:
        from northcord.utils.config import ConfigManager
        config = ConfigManager()
        main_token = config.get_token()
        if main_token and not main_token.startswith("test_"):
            tokens = [main_token]

    if not tokens:
        print("❌ No tokens found in data/tokens.txt or config.json.")
        print("   Please configure at least one token.")
        sys.exit(1)

    print(f"📋 Loaded {len(tokens)} token(s) from settings. Verifying accounts...")
    print()

    # Verify all loaded tokens in parallel
    validation_results = await asyncio.gather(*(validate_token_info(t) for t in tokens))
    
    valid_accounts = []
    print("Token Verification Status:")
    print("─" * 60)
    for idx, (t, ok, detail) in enumerate(validation_results, 1):
        masked = t[:15] + "..." if len(t) > 15 else t
        if ok:
            print(f" #{idx:<2} | {masked:<20} | Status: Valid (User: {detail})")
            valid_accounts.append((t, detail))
        else:
            print(f" #{idx:<2} | {masked:<20} | Status: Invalid ({detail})")
    print("─" * 60)
    print()

    if not valid_accounts:
        print("❌ No valid tokens validated successfully. Cannot launch VC joiner.")
        sys.exit(1)

    print(f"🚀 Found {len(valid_accounts)} valid account(s) ready to join.")
    print()

    guild_id = input("Enter Guild ID (Server ID): ").strip()
    channel_id = input("Enter Channel ID (Voice Channel ID): ").strip()
    
    mute_input = input("Mute microphone? (y/n) [y]: ").strip().lower()
    mute = mute_input in ("", "y", "yes")
    
    deaf_input = input("Deafen audio? (y/n) [y]: ").strip().lower()
    deaf = deaf_input in ("", "y", "yes")

    print()
    print("⏳ Connecting tokens. Press Ctrl+C to disconnect and exit...")
    print()

    tasks = [join_token(token, username, guild_id, channel_id, mute, deaf) for token, username in valid_accounts]
    
    try:
        await asyncio.gather(*tasks)
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"❌ Error during execution: {e}")
    finally:
        print()
        print("👋 Disconnecting and exiting...")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Disconnecting and exiting...")
