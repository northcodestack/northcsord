from __future__ import annotations

from datetime import datetime
from typing import Any

from textual.app import ComposeResult
from textual.widgets import Static, Label, ListView, ListItem
from textual.containers import Horizontal, Vertical


class MessageWidget(Static):
    def __init__(
        self,
        author: str,
        content: str,
        timestamp: str | None = None,
        author_color: str | None = None,
        is_reply: bool = False,
        reply_to: str | None = None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self._author = author
        self._content = content
        self._timestamp = timestamp
        self._author_color = author_color
        self._is_reply = is_reply
        self._reply_to = reply_to

    def compose(self) -> ComposeResult:
        with Vertical(classes="message-container"):
            if self._is_reply and self._reply_to:
                yield Label(f"Replying to {self._reply_to}", classes="reply-indicator")
            with Horizontal(classes="message-header"):
                author_label = Label(
                    self._author,
                    classes="message-author",
                )
                if self._author_color:
                    author_label.styles.color = self._author_color
                yield author_label
                if self._timestamp:
                    yield Label(
                        self._format_timestamp(self._timestamp),
                        classes="message-timestamp",
                    )
            yield Label(self._content, classes="message-content")

    def _format_timestamp(self, timestamp: str) -> str:
        try:
            dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            return dt.strftime("%H:%M")
        except (ValueError, TypeError):
            return timestamp


class MessageList(ListView):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._messages: list[dict[str, Any]] = []

    def add_message(
        self,
        author: str,
        content: str,
        message_id: str | None = None,
        timestamp: str | None = None,
        author_color: str | None = None,
        is_reply: bool = False,
        reply_to: str | None = None,
    ) -> None:
        msg_data = {
            "id": message_id,
            "author": author,
            "content": content,
            "timestamp": timestamp,
            "author_color": author_color,
            "is_reply": is_reply,
            "reply_to": reply_to,
        }
        self._messages.append(msg_data)

        widget = MessageWidget(
            author=author,
            content=content,
            timestamp=timestamp,
            author_color=author_color,
            is_reply=is_reply,
            reply_to=reply_to,
        )
        item = ListItem(widget)
        if self.is_mounted:
            try:
                self.append(item)
                self.scroll_end(animate=False)
            except Exception:
                pass

    def load_messages(self, messages: list[dict[str, Any]]) -> None:
        if self.is_mounted:
            try:
                self.clear()
            except Exception:
                pass
        self._messages = []
        for msg in reversed(messages):
            author = msg.get("author", {})
            author_name = author.get("global_name") or author.get("username", "Unknown")
            content = msg.get("content", "")
            timestamp = msg.get("timestamp")
            message_id = msg.get("id")

            self.add_message(
                author=author_name,
                content=content,
                message_id=message_id,
                timestamp=timestamp,
            )

    def clear_messages(self) -> None:
        if self.is_mounted:
            try:
                self.clear()
            except Exception:
                pass
        self._messages = []

    def start_reply(self) -> None:
        pass
