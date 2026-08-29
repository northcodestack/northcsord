from __future__ import annotations

from typing import Any, Callable


class Command:
    def __init__(
        self,
        name: str,
        func: Callable,
        description: str,
        usage: str | None = None,
    ):
        self.name = name
        self.func = func
        self.description = description
        self.usage = usage or f"/{name}"


class CommandHandler:
    def __init__(self, discord_client: Any = None, gateway: Any = None, voice: Any = None):
        self.discord = discord_client
        self.gateway = gateway
        self.voice = voice
        self._commands: dict[str, Command] = {}
        self._register_defaults()

    def _register_defaults(self) -> None:
        self.register("help", self._cmd_help, "Show all commands", "/help [command]")
        self.register("join", self._cmd_join, "Join voice channel", "/join")
        self.register("leave", self._cmd_leave, "Leave voice channel", "/leave")
        self.register("play", self._cmd_play, "Play audio in VC", "/play <file>")
        self.register("stop", self._cmd_stop, "Stop audio playback", "/stop")
        self.register("pause", self._cmd_pause, "Pause audio", "/pause")
        self.register("resume", self._cmd_resume, "Resume audio", "/resume")
        self.register("volume", self._cmd_volume, "Set volume (0-200)", "/volume <0-200>")
        self.register("loop", self._cmd_loop, "Toggle loop playback", "/loop")
        self.register("upload", self._cmd_upload, "Upload file", "/upload <file>")
        self.register("status", self._cmd_status, "Set custom status", "/status <text>")
        self.register("server", self._cmd_server, "Switch server", "/server <name>")
        self.register("channel", self._cmd_channel, "Switch channel", "/channel <name>")
        self.register("theme", self._cmd_theme, "Change theme", "/theme <name>")
        self.register("purge", self._cmd_purge, "Delete n messages", "/purge <n>")
        self.register("mute", self._cmd_mute, "Mute microphone", "/mute")
        self.register("deafen", self._cmd_deafen, "Deafen", "/deafen")
        self.register("invite", self._cmd_invite, "Create invite", "/invite")
        self.register("profile", self._cmd_profile, "View your profile", "/profile")
        self.register("search", self._cmd_search, "Search messages", "/search <text>")
        self.register("reply", self._cmd_reply, "Reply to last message", "/reply <text>")
        self.register("emoji", self._cmd_emoji, "Send emoji", "/emoji <name>")
        self.register("typing", self._cmd_typing, "Trigger typing indicator", "/typing")
        self.register("clear", self._cmd_clear, "Clear chat", "/clear")
        self.register("exit", self._cmd_exit, "Exit NorthCord", "/exit")

    def register(
        self,
        name: str,
        func: Callable,
        description: str = "",
        usage: str | None = None,
    ) -> None:
        self._commands[name.lower()] = Command(name.lower(), func, description, usage)

    def execute(self, command: str) -> str | None:
        if not command.startswith("/"):
            return None

        parts = command[1:].split()
        if not parts:
            return None

        name = parts[0].lower()
        args = parts[1:]

        cmd = self._commands.get(name)
        if not cmd:
            suggestions = self._get_suggestions(name)
            msg = f"Unknown command: /{name}."
            if suggestions:
                msg += f" Did you mean: /{', /'.join(suggestions)}?"
            else:
                msg += " Type /help for available commands."
            return msg

        try:
            result = cmd.func(args)
            if isinstance(result, str):
                return result
            return None
        except Exception as e:
            return f"Error executing /{name}: {e}"

    def get_help(self, command: str | None = None) -> str:
        if command:
            cmd = self._commands.get(command.lower())
            if not cmd:
                return f"Unknown command: /{command}"
            lines = [
                f"Command: /{cmd.name}",
                f"Description: {cmd.description}",
                f"Usage: {cmd.usage}",
            ]
            return "\n".join(lines)

        lines = ["NorthCord Commands", "══════════════════", ""]
        for cmd in self._commands.values():
            lines.append(f"  {cmd.usage:<25s} {cmd.description}")
        return "\n".join(lines)

    def get_completions(self, partial: str) -> list[str]:
        partial = partial.lower()
        return [
            f"/{cmd.name}"
            for cmd in self._commands.values()
            if cmd.name.startswith(partial)
        ]

    def _get_suggestions(self, name: str) -> list[str]:
        suggestions = []
        for cmd_name in self._commands:
            if len(name) >= 2:
                if name in cmd_name or cmd_name.startswith(name):
                    suggestions.append(cmd_name)
        return suggestions[:3]

    def _cmd_help(self, args: list[str]) -> str:
        return self.get_help(args[0] if args else None)

    def _cmd_join(self, args: list[str]) -> str:
        return "Joining voice channel..."

    def _cmd_leave(self, args: list[str]) -> str:
        return "Leaving voice channel..."

    def _cmd_play(self, args: list[str]) -> str:
        if not args:
            return "Usage: /play <file> - Play an audio file in voice chat"
        return f"Playing '{args[0]}'..."

    def _cmd_stop(self, args: list[str]) -> str:
        return "Stopping playback..."

    def _cmd_pause(self, args: list[str]) -> str:
        return "Pausing playback..."

    def _cmd_resume(self, args: list[str]) -> str:
        return "Resuming playback..."

    def _cmd_volume(self, args: list[str]) -> str:
        if not args:
            return "Usage: /volume <0-200> - Set volume level"
        try:
            vol = int(args[0])
            if 0 <= vol <= 200:
                return f"Volume set to {vol}%"
            return "Volume must be between 0 and 200"
        except ValueError:
            return "Volume must be a number"

    def _cmd_loop(self, args: list[str]) -> str:
        return "Loop toggled"

    def _cmd_upload(self, args: list[str]) -> str:
        if not args:
            return "Usage: /upload <file> - Upload a file to the current channel"
        return f"Uploading '{args[0]}'..."

    def _cmd_status(self, args: list[str]) -> str:
        if not args:
            return "Usage: /status <text> - Set your custom status"
        status_text = " ".join(args)
        if self.gateway:
            import asyncio
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(
                    self.gateway.update_presence(status="online", activity={"name": status_text, "type": 4})
                )
            except Exception:
                pass
        return f"Status set to '{status_text}'"

    def _cmd_server(self, args: list[str]) -> str:
        if not args:
            return "Usage: /server <name> - Switch to a server"
        return f"Switching to server '{' '.join(args)}'..."

    def _cmd_channel(self, args: list[str]) -> str:
        if not args:
            return "Usage: /channel <name> - Switch to a channel"
        return f"Switching to channel '{' '.join(args)}'..."

    def _cmd_theme(self, args: list[str]) -> str:
        if not args:
            return "Usage: /theme <name> - Change theme. Available: dark, light, midnight, solarized, monokai"
        return f"Theme changed to '{args[0]}'"

    def _cmd_purge(self, args: list[str]) -> str:
        if not args:
            return "Usage: /purge <n> - Delete the last n messages"
        try:
            n = int(args[0])
            if n < 1:
                return "Number must be positive"
            if n > 100:
                return "Cannot purge more than 100 messages at once"
            return f"Purging {n} messages..."
        except ValueError:
            return "Please provide a valid number"

    def _cmd_mute(self, args: list[str]) -> str:
        return "Microphone muted" if not args else "Microphone unmuted"

    def _cmd_deafen(self, args: list[str]) -> str:
        return "Deafened" if not args else "Undeafened"

    def _cmd_invite(self, args: list[str]) -> str:
        return "Creating invite link..."

    def _cmd_profile(self, args: list[str]) -> str:
        if self.discord and self.discord.user:
            user = self.discord.user
            return (
                f"Profile: {user.get('global_name') or user.get('username', 'Unknown')}"
                f"\nID: {user.get('id', 'N/A')}"
                f"\nBot: {'Yes' if user.get('bot') else 'No'}"
            )
        return "Not connected to Discord"

    def _cmd_search(self, args: list[str]) -> str:
        if not args:
            return "Usage: /search <text> - Search messages in current channel"
        return f"Searching for '{" ".join(args)}'..."

    def _cmd_reply(self, args: list[str]) -> str:
        if not args:
            return "Usage: /reply <text> - Reply to the last message"
        return f"Replying: {' '.join(args)}"

    def _cmd_emoji(self, args: list[str]) -> str:
        if not args:
            return "Usage: /emoji <name> - Send an emoji"
        return f"Sending emoji '{args[0]}'..."

    def _cmd_typing(self, args: list[str]) -> str:
        return "Typing indicator triggered"

    def _cmd_clear(self, args: list[str]) -> str:
        return "Chat cleared"

    def _cmd_exit(self, args: list[str]) -> str:
        return "Exiting NorthCord. Goodbye!"

    @property
    def commands(self) -> dict[str, Command]:
        return dict(self._commands)

    def get(self, name: str) -> Command | None:
        return self._commands.get(name.lower())
