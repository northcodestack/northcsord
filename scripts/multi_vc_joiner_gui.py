#!/usr/bin/env python3
import asyncio
import json
import os
import random
import sys
import threading
import time
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent.parent))

from northcord.core.discord import DiscordClient
from northcord.core.gateway import GatewayClient

TOKENS_FILE = Path(__file__).parent.parent / "data" / "tokens.txt"

class AsyncLoop:
    def __init__(self):
        self.loop: asyncio.AbstractEventLoop | None = None
        self._thread: threading.Thread | None = None

    def start(self):
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        while self.loop is None:
            time.sleep(0.01)

    def _run(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()

    def stop(self):
        if self.loop and self.loop.is_running():
            self.loop.call_soon_threadsafe(self.loop.stop)

    def run(self, coro) -> asyncio.Future:
        return asyncio.run_coroutine_threadsafe(coro, self.loop)


class TokenEntry:
    def __init__(self, token: str):
        self.token = token.strip().strip("\"'")
        self.username = "?"
        self.valid = False
        self.gateway: GatewayClient | None = None
        self.joined = False
        self.guild_id: str = ""
        self.channel_id: str = ""


class VCJoinerGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("NorthCord - VC Joiner")
        self.geometry("750x680")
        self.resizable(True, True)

        self.async_loop = AsyncLoop()
        self.async_loop.start()

        self.tokens: list[TokenEntry] = []
        self.guilds: list[dict[str, Any]] = []
        self.channels: list[dict[str, Any]] = []
        self._join_task: asyncio.Task | None = None
        self._leave_task: asyncio.Task | None = None

        self._build_ui()
        self._load_tokens()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_ui(self):
        main = ttk.Frame(self, padding=8)
        main.pack(fill="both", expand=True)

        # Token input
        row = ttk.Frame(main)
        row.pack(fill="x", pady=(0, 4))
        ttk.Label(row, text="Tokens (one per line):").pack(anchor="w")
        self.token_text = scrolledtext.ScrolledText(main, height=5, font=("Consolas", 9))
        self.token_text.pack(fill="x", pady=(0, 4))

        # Buttons row
        btn_row = ttk.Frame(main)
        btn_row.pack(fill="x", pady=(0, 6))
        self.add_btn = ttk.Button(btn_row, text="Add Tokens", command=self._add_tokens)
        self.add_btn.pack(side="left", padx=(0, 4))
        self.validate_btn = ttk.Button(btn_row, text="Validate", command=self._validate_tokens)
        self.validate_btn.pack(side="left", padx=4)
        self.load_btn = ttk.Button(btn_row, text="Load Servers", command=self._load_guilds, state="disabled")
        self.load_btn.pack(side="left", padx=4)
        self.clear_btn = ttk.Button(btn_row, text="Clear All", command=self._clear_tokens)
        self.clear_btn.pack(side="left", padx=4)

        # Token treeview
        tree_frame = ttk.LabelFrame(main, text="Accounts", padding=4)
        tree_frame.pack(fill="both", expand=True, pady=(0, 6))
        columns = ("token", "username", "status")
        self.tree = ttk.Treeview(tree_frame, columns=columns, show="headings", height=6)
        self.tree.heading("token", text="Token")
        self.tree.heading("username", text="User")
        self.tree.heading("status", text="Status")
        self.tree.column("token", width=200)
        self.tree.column("username", width=120)
        self.tree.column("status", width=100)
        scroll_tree = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll_tree.set)
        self.tree.pack(side="left", fill="both", expand=True)
        scroll_tree.pack(side="right", fill="y")

        # Guild / Channel selection
        sel_row = ttk.Frame(main)
        sel_row.pack(fill="x", pady=(0, 6))
        ttk.Label(sel_row, text="Server:").pack(side="left")
        self.guild_combo = ttk.Combobox(sel_row, width=30, state="readonly")
        self.guild_combo.pack(side="left", padx=(4, 12))
        self.guild_combo.bind("<<ComboboxSelected>>", self._on_guild_select)
        ttk.Label(sel_row, text="Channel:").pack(side="left")
        self.channel_combo = ttk.Combobox(sel_row, width=30, state="readonly")
        self.channel_combo.pack(side="left", padx=(4, 0))

        # Action buttons
        action_row = ttk.Frame(main)
        action_row.pack(fill="x", pady=(0, 6))
        self.join_btn = ttk.Button(action_row, text="Join All", command=self._join_all, state="disabled")
        self.join_btn.pack(side="left", padx=(0, 8))
        self.leave_btn = ttk.Button(action_row, text="Leave All", command=self._leave_all, state="disabled")
        self.leave_btn.pack(side="left", padx=8)
        ttk.Label(action_row, text="Delay:").pack(side="left", padx=(24, 4))
        self.delay_var = tk.StringVar(value="1.5")
        delay_spin = ttk.Spinbox(action_row, from_=0.0, to=5.0, increment=0.1, textvariable=self.delay_var, width=5)
        delay_spin.pack(side="left")
        ttk.Label(action_row, text="sec").pack(side="left")

        # Log
        log_frame = ttk.LabelFrame(main, text="Log", padding=4)
        log_frame.pack(fill="x")
        self.log_text = scrolledtext.ScrolledText(log_frame, height=8, font=("Consolas", 9), state="disabled")
        self.log_text.pack(fill="both", expand=True)

    def _log(self, msg: str):
        self.log_text.configure(state="normal")
        self.log_text.insert("end", msg + "\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def _mask_token(self, token: str) -> str:
        return token[:12] + "..." + token[-4:] if len(token) > 20 else token[:8] + "..."

    def _refresh_tree(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        for te in self.tokens:
            status = "Valid" if te.valid else ("Invalid" if te.username != "?" else "Pending")
            if te.joined:
                status = "Joined"
            self.tree.insert("", "end", values=(self._mask_token(te.token), te.username, status))

    def _load_tokens(self):
        if TOKENS_FILE.exists():
            with open(TOKENS_FILE, encoding="utf-8") as f:
                lines = [l.strip() for l in f if l.strip() and not l.startswith("#") and "PASTE" not in l]
            for line in lines:
                self.tokens.append(TokenEntry(line))
            self._refresh_tree()
            self._log(f"Loaded {len(lines)} token(s) from data/tokens.txt")

    def _save_tokens(self):
        TOKENS_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(TOKENS_FILE, "w", encoding="utf-8") as f:
            for te in self.tokens:
                f.write(te.token + "\n")

    def _add_tokens(self):
        raw = self.token_text.get("1.0", "end").strip()
        if not raw:
            return
        new_count = 0
        for line in raw.splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                existing_tokens = {te.token for te in self.tokens}
                t = line.strip("\"'")
                if t not in existing_tokens:
                    self.tokens.append(TokenEntry(t))
                    new_count += 1
        if new_count:
            self._save_tokens()
            self._refresh_tree()
            self._log(f"Added {new_count} new token(s)")
            self.token_text.delete("1.0", "end")
        else:
            self._log("No new tokens to add")

    def _clear_tokens(self):
        if not self.tokens:
            return
        if messagebox.askyesno("Clear", "Remove all tokens?"):
            self.tokens.clear()
            self._save_tokens()
            self._refresh_tree()
            self._log("All tokens cleared")

    def _validate_tokens(self):
        if not self.tokens:
            messagebox.showinfo("Info", "No tokens to validate")
            return
        self._log("Validating tokens...")
        self.validate_btn.configure(state="disabled")
        self.async_loop.run(self._do_validate())

    async def _do_validate(self):
        for te in self.tokens:
            dc = DiscordClient(te.token)
            try:
                ok = await dc.validate_token()
                te.valid = ok
                te.username = dc.user.get("username", "?") if ok else "Invalid"
            except Exception as e:
                te.valid = False
                te.username = str(e)[:20]
        self.after(0, self._on_validate_done)

    def _on_validate_done(self):
        self._refresh_tree()
        self.validate_btn.configure(state="normal")
        valid_count = sum(1 for te in self.tokens if te.valid)
        self._log(f"Validation done: {valid_count}/{len(self.tokens)} valid")
        self.load_btn.configure(state="normal" if valid_count else "disabled")

    def _load_guilds(self):
        valid = [te for te in self.tokens if te.valid]
        if not valid:
            messagebox.showinfo("Info", "No valid tokens")
            return
        self._log("Loading servers...")
        self.load_btn.configure(state="disabled")
        self.async_loop.run(self._do_load_guilds(valid[0].token))

    async def _do_load_guilds(self, token: str):
        dc = DiscordClient(token)
        guilds = await dc.get_guilds()
        self.guilds = guilds
        self.after(0, self._on_guilds_loaded)

    def _on_guilds_loaded(self):
        self.load_btn.configure(state="normal")
        if not self.guilds:
            self._log("No servers found")
            return
        names = [f"{g['name']} ({g['id']})" for g in self.guilds]
        self.guild_combo["values"] = names
        if names:
            self.guild_combo.current(0)
        self._log(f"Loaded {len(self.guilds)} server(s)")
        self._on_guild_select()

    def _on_guild_select(self, event=None):
        idx = self.guild_combo.current()
        if idx < 0 or idx >= len(self.guilds):
            return
        gid = self.guilds[idx]["id"]
        self._log(f"Loading channels for {self.guilds[idx]['name']}...")
        self.async_loop.run(self._do_load_channels(gid))

    async def _do_load_channels(self, guild_id: str):
        valid = [te for te in self.tokens if te.valid]
        if not valid:
            return
        dc = DiscordClient(valid[0].token)
        channels = await dc.get_channels(guild_id)
        voice = [c for c in channels if c.get("type") == 2]
        self.channels = voice
        self.after(0, self._on_channels_loaded)

    def _on_channels_loaded(self):
        if not self.channels:
            self._log("No voice channels found")
            self.channel_combo["values"] = []
            return
        names = [f"{c['name']} ({c['id']})" for c in self.channels]
        self.channel_combo["values"] = names
        if names:
            self.channel_combo.current(0)
        self._log(f"Loaded {len(self.channels)} voice channel(s)")
        self.join_btn.configure(state="normal")

    def _join_all(self):
        idx = self.channel_combo.current()
        if idx < 0 or idx >= len(self.channels):
            messagebox.showinfo("Info", "Select a channel first")
            return
        channel = self.channels[idx]
        guild_id = channel["guild_id"]
        channel_id = channel["id"]
        delay_base = float(self.delay_var.get())
        self._set_actions_disabled(True)
        self._log("Joining all tokens to VC...")
        self.async_loop.run(self._do_join_all(guild_id, channel_id, delay_base))

    async def _do_join_all(self, guild_id: str, channel_id: str, delay_base: float):
        valid = [te for te in self.tokens if te.valid]
        for te in valid:
            delay = max(0.3, delay_base + random.uniform(-0.4, 0.4))
            self.after(0, lambda t=te, d=delay: self._log(f"Joining {t.username} in {d:.1f}s..."))
            try:
                gw = GatewayClient(te.token)
                connected = asyncio.Event()

                def on_ready(evt_type: str, _data: dict[str, Any]):
                    if evt_type == "READY":
                        connected.set()

                gw.on_event = on_ready
                await gw.connect()
                try:
                    await asyncio.wait_for(connected.wait(), timeout=10)
                except asyncio.TimeoutError:
                    self.after(0, lambda t=te: self._log(f"Timeout connecting {t.username}"))
                    continue

                await gw.update_voice_state(guild_id, channel_id, False, False)
                te.gateway = gw
                te.joined = True
                self.after(0, lambda t=te: self._log(f"Joined {t.username}"))
                self.after(0, self._refresh_tree)

                await asyncio.sleep(delay)
            except Exception as e:
                self.after(0, lambda t=te, err=e: self._log(f"Error {t.username}: {err}"))

        self.after(0, self._on_join_done)

    def _on_join_done(self):
        self._set_actions_disabled(False)
        self.leave_btn.configure(state="normal")
        self._log("Join complete")

    def _leave_all(self):
        delay_base = float(self.delay_var.get())
        self._set_actions_disabled(True)
        self._log("Leaving all VCs...")
        self.async_loop.run(self._do_leave_all(delay_base))

    async def _do_leave_all(self, delay_base: float):
        for te in self.tokens:
            if te.gateway and te.joined:
                delay = max(0.3, delay_base + random.uniform(-0.4, 0.4))
                self.after(0, lambda t=te, d=delay: self._log(f"Leaving {t.username} in {d:.1f}s..."))
                try:
                    await te.gateway.update_voice_state("", None, False, False)
                    await te.gateway.disconnect()
                    te.joined = False
                    te.gateway = None
                    self.after(0, lambda t=te: self._log(f"Left {t.username}"))
                    self.after(0, self._refresh_tree)
                    await asyncio.sleep(delay)
                except Exception as e:
                    self.after(0, lambda t=te, err=e: self._log(f"Error leaving {t.username}: {err}"))

        self.after(0, self._on_leave_done)

    def _on_leave_done(self):
        self._set_actions_disabled(False)
        self.leave_btn.configure(state="disabled")
        self.join_btn.configure(state="normal" if self.channels else "disabled")
        self._log("Leave complete")

    def _set_actions_disabled(self, disabled: bool):
        state = "disabled" if disabled else "normal"
        self.join_btn.configure(state=state)
        self.leave_btn.configure(state=state)
        self.add_btn.configure(state=state)
        self.validate_btn.configure(state=state)
        self.load_btn.configure(state=state)
        self.clear_btn.configure(state=state)

    def _on_close(self):
        self._log("Shutting down...")
        if self._join_task and not self._join_task.done():
            self._join_task.cancel()
        if self._leave_task and not self._leave_task.done():
            self._leave_task.cancel()
        for te in self.tokens:
            if te.gateway:
                try:
                    asyncio.run_coroutine_threadsafe(te.gateway.disconnect(), self.async_loop.loop)
                except Exception:
                    pass
        self.async_loop.stop()
        self.destroy()


def main():
    app = VCJoinerGUI()
    app.mainloop()


if __name__ == "__main__":
    main()
