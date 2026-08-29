from __future__ import annotations

import re
from datetime import datetime


def format_timestamp(timestamp: str, fmt: str = "%H:%M") -> str:
    if not timestamp:
        return ""
    try:
        dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        return dt.strftime(fmt)
    except (ValueError, TypeError):
        return timestamp


def truncate(text: str, max_length: int = 200, suffix: str = "...") -> str:
    if len(text) <= max_length:
        return text
    return text[: max_length - len(suffix)].rstrip() + suffix


def sanitize_input(text: str) -> str:
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def parse_mentions(text: str) -> list[str]:
    return re.findall(r"<@!?(\d+)>", text)


def parse_emojis(text: str) -> list[str]:
    return re.findall(r"[^\w\s]", text)


def parse_channels(text: str) -> list[str]:
    return re.findall(r"<#(\d+)>", text)
