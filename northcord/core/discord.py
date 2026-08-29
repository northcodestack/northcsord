from __future__ import annotations

import asyncio
import json
import os
import re
import time
from pathlib import Path
from typing import Any, Callable

import requests
from requests.adapters import HTTPAdapter
import urllib3
from urllib3.util.retry import Retry

from northcord.utils.logger import get_logger

logger = get_logger(__name__)

# Disable requests SSL warnings globally when testing under non-standard cert environments
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

API_BASE = "https://discord.com/api/v10"
MAX_RETRIES = 3
BASE_DELAY = 1.0
MAX_DELAY = 60.0


class RateLimiter:
    """Simple rate limiter for Discord API"""
    
    def __init__(self):
        self.limits = {}  # route -> {remaining, reset_at}
        self._lock = asyncio.Lock()
    
    async def acquire(self, route: str):
        """Wait if rate limited"""
        async with self._lock:
            if route in self.limits:
                limit = self.limits[route]
                if limit.get("remaining", 1) <= 0:
                    wait_time = limit.get("reset_at", time.time()) - time.time()
                    if wait_time > 0:
                        logger.debug("Rate limited on %s, waiting %.2fs", route, wait_time)
                        await asyncio.sleep(wait_time + 0.1)
    
    def update(self, route: str, response: requests.Response):
        """Update rate limit info from response headers"""
        remaining = response.headers.get("X-RateLimit-Remaining")
        reset_at = response.headers.get("X-RateLimit-Reset")
        
        if remaining is not None:
            self.limits[route] = {
                "remaining": int(remaining),
                "reset_at": float(reset_at) if reset_at else time.time() + 60
            }


def sanitize_token(raw_token: str | Any) -> str | None:
    if not raw_token:
        return None
    raw = str(raw_token)
    raw = raw.strip()
    raw = raw.strip("\"'.,; \t\n\r\u2018\u2019\u201c\u201d")
    raw = raw.strip()
    return raw if raw else None


class DiscordClient:
    """Discord API Client with fixed token validation"""

    def __init__(self, token: str | Any):
        if hasattr(token, "get_token"):
            raw = token.get_token()
        elif hasattr(token, "get"):
            raw = token.get("token")
        else:
            raw = token

        self.token = sanitize_token(raw)

        self.user = None
        self.last_error = None
        self.rate_limiter = RateLimiter()
        self._closed = False
        
        # Create session with retry strategy
        self.session = self._create_session()
    
    def _create_session(self) -> requests.Session:
        """Create requests session with retry strategy"""
        session = requests.Session()
        
        # Retry strategy for connection errors
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "POST", "PUT", "DELETE", "PATCH"]
        )
        
        adapter = HTTPAdapter(
            max_retries=retry_strategy,
            pool_connections=10,
            pool_maxsize=10
        )
        session.mount("https://", adapter)
        session.mount("http://", adapter)
        
        return session
    
    def _build_headers(self) -> dict[str, str]:
        """Build request headers with proper formatting"""
        token = self.token
        if not token:
            return {}
        
        if token.startswith(("Bot ", "MFA ")):
            authorization = token
        else:
            authorization = token
        
        # Use real browser user-agent and headers to avoid blocking
        headers = {
            "Authorization": authorization,
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept-Language": "en-US,en;q=0.9",
            "Connection": "keep-alive",
            "Sec-Ch-Ua": '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": '"Windows"',
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
        }
        
        return headers
    
    def _route_key(self, method: str, url: str) -> str:
        """Generate route key for rate limiting"""
        if url.startswith(API_BASE):
            path = url[len(API_BASE):]
        else:
            path = url
        
        # Remove IDs from path for rate limiting
        path = re.sub(r'/\d+', '/:id', path)
        return f"{method}:{path}"
    
    async def _request(
        self,
        method: str,
        path: str,
        **kwargs
    ) -> dict | list | None:
        """Make API request with proper error handling"""
        if path.startswith("http"):
            url = path
        else:
            url = f"{API_BASE}{path}"
        
        route = self._route_key(method, url)
        
        # Default headers
        headers = self._build_headers()
        if "headers" in kwargs:
            headers.update(kwargs["headers"])
        kwargs["headers"] = headers
        
        # Default timeout
        if "timeout" not in kwargs:
            kwargs["timeout"] = 30
        
        logger.debug("Request: %s %s", method, url)
        
        for attempt in range(MAX_RETRIES):
            try:
                # Rate limiting
                await self.rate_limiter.acquire(route)
                
                # Make request with SSL verification
                response = self.session.request(
                    method,
                    url,
                    verify=True,  # Enable SSL verification
                    **kwargs
                )
                
                # Update rate limiter
                self.rate_limiter.update(route, response)
                
                # Check for rate limit
                if response.status_code == 429:
                    retry_after = float(response.headers.get("Retry-After", BASE_DELAY))
                    logger.warning("Rate limited, waiting %.2fs", retry_after)
                    await asyncio.sleep(min(retry_after, MAX_DELAY))
                    continue
                
                # Handle errors
                if response.status_code == 401:
                    self.last_error = "401 Unauthorized - Invalid Token"
                    logger.error(self.last_error)
                    return None
                
                if response.status_code == 403:
                    self.last_error = "403 Forbidden - Missing Permissions"
                    logger.error(self.last_error)
                    return None
                
                if response.status_code == 404:
                    self.last_error = "404 Not Found"
                    logger.warning(self.last_error)
                    return None
                
                # Success
                if response.status_code == 204:
                    return {}
                
                response.raise_for_status()
                
                # Parse JSON response
                try:
                    return response.json()
                except json.JSONDecodeError:
                    logger.warning("Invalid JSON response: %s", response.text[:200])
                    return {"raw": response.text}
                
            except requests.exceptions.SSLError as e:
                logger.error("SSL Error: %s", e)
                self.last_error = f"SSL Error: {e}"
                return None
                
            except requests.exceptions.ConnectionError as e:
                logger.error("Connection Error: %s", e)
                self.last_error = f"Connection Error: {e}"
                if attempt < MAX_RETRIES - 1:
                    await asyncio.sleep(min(BASE_DELAY * (2 ** attempt), MAX_DELAY))
                    continue
                return None
                
            except requests.exceptions.Timeout as e:
                logger.error("Timeout: %s", e)
                self.last_error = f"Timeout: {e}"
                if attempt < MAX_RETRIES - 1:
                    await asyncio.sleep(min(BASE_DELAY * (2 ** attempt), MAX_DELAY))
                    continue
                return None
                
            except requests.exceptions.RequestException as e:
                logger.error("Request Failed: %s", e)
                self.last_error = f"Request Failed: {e}"
                return None
        
        return None
    
    async def validate_token(self) -> bool:
        """
        Validate the token by fetching the current user.
        Returns True if valid, False otherwise.
        """
        self.last_error = None

        if not self.token:
            self.last_error = "No token provided"
            return False

        if len(self.token) < 10:
            self.last_error = f"Token too short ({len(self.token)} chars), expected 50+"
            return False

        try:
            result = await self._request("GET", "/users/@me")

            if result and isinstance(result, dict):
                self.user = result
                username = result.get("username", "Unknown")
                logger.info("Token valid. Logged in as %s", username)
                return True

            if self.last_error:
                logger.error("Token validation failed: %s", self.last_error)
            else:
                logger.error("Token validation failed: request returned non-dict or empty")
                self.last_error = "Request returned non-dict or empty"

            return False

        except Exception as e:
            logger.error("Token validation exception: %s", e)
            self.last_error = f"Exception: {e}"
            return False

    async def get_user(self) -> dict[str, Any] | None:
        if self.user:
            return self.user
        result = await self._request("GET", "/users/@me")
        if isinstance(result, dict):
            self.user = result
        return self.user

    async def get_guilds(self) -> list[dict[str, Any]]:
        result = await self._request("GET", "/users/@me/guilds")
        return result if isinstance(result, list) else []

    async def get_channels(self, guild_id: str) -> list[dict[str, Any]]:
        result = await self._request("GET", f"/guilds/{guild_id}/channels")
        return result if isinstance(result, list) else []

    async def get_messages(self, channel_id: str, limit: int = 100) -> list[dict[str, Any]]:
        limit = min(max(limit, 1), 100)
        result = await self._request("GET", f"/channels/{channel_id}/messages", params={"limit": limit, "around": None})
        if isinstance(result, list):
            return list(reversed(result))
        return []

    async def send_message(self, channel_id: str, content: str) -> dict[str, Any] | None:
        payload = {"content": content}
        result = await self._request("POST", f"/channels/{channel_id}/messages", json=payload)
        return result if isinstance(result, dict) else None

    async def upload_file(self, channel_id: str, file_path: str) -> dict[str, Any] | None:
        path = Path(file_path)
        if not path.exists():
            logger.error("File not found: %s", file_path)
            return None

        try:
            file_size = path.stat().st_size
            if file_size > 25 * 1024 * 1024:
                logger.error("File too large (max 25MB): %s", file_path)
                return None

            file_name = path.name
            with open(path, "rb") as f:
                files = {"file": (file_name, f, self._guess_mime(file_name))}
                payload = {"content": ""}
                headers = self._build_headers()
                headers.pop("Content-Type", None)
                resp = self.session.post(
                    f"{API_BASE}/channels/{channel_id}/messages",
                    headers=headers,
                    data=payload,
                    files=files,
                )
                if resp.status_code == 429:
                    retry_after = float(resp.headers.get("Retry-After", BASE_DELAY))
                    logger.warning("Rate limited on upload, waiting %.2fs", retry_after)
                    await asyncio.sleep(min(retry_after, MAX_DELAY))
                    return None
                resp.raise_for_status()
                return resp.json()

        except requests.RequestException as e:
            logger.error("Upload failed: %s", e)
            return None

    def _guess_mime(self, filename: str) -> str:
        ext = Path(filename).suffix.lower()
        mime_map: dict[str, str] = {
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".gif": "image/gif",
            ".webp": "image/webp",
            ".mp4": "video/mp4",
            ".webm": "video/webm",
            ".mp3": "audio/mpeg",
            ".wav": "audio/wav",
            ".ogg": "audio/ogg",
            ".pdf": "application/pdf",
            ".zip": "application/zip",
            ".txt": "text/plain",
            ".json": "application/json",
        }
        return mime_map.get(ext, "application/octet-stream")

    async def join_voice(self, guild_id: str, channel_id: str) -> bool:
        result = await self._request(
            "PATCH",
            f"/guilds/{guild_id}/members/@me",
            json={"channel_id": channel_id},
        )
        return result is not None

    async def leave_voice(self) -> bool:
        if not self.user:
            return False
        guilds = await self.get_guilds()
        for guild in guilds:
            await self._request(
                "PATCH",
                f"/guilds/{guild['id']}/members/@me",
                json={"channel_id": None},
            )
        return True

    async def create_invite(self, channel_id: str, max_age: int = 86400, max_uses: int = 0) -> dict[str, Any] | None:
        payload = {
            "max_age": max_age,
            "max_uses": max_uses,
            "temporary": False,
        }
        result = await self._request("POST", f"/channels/{channel_id}/invites", json=payload)
        return result if isinstance(result, dict) else None

    async def delete_messages(self, channel_id: str, message_ids: list[str]) -> bool:
        if len(message_ids) == 1:
            result = await self._request("DELETE", f"/channels/{channel_id}/messages/{message_ids[0]}")
            return result is not None
        if len(message_ids) > 100:
            logger.error("Cannot delete more than 100 messages at once")
            return False
        payload = {"messages": message_ids}
        result = await self._request("POST", f"/channels/{channel_id}/messages/bulk-delete", json=payload)
        return result is not None

    async def set_status(self, status: str, activity: dict[str, Any] | None = None) -> bool:
        from northcord.core.gateway import GatewayClient

        valid_statuses = {"online", "idle", "dnd", "invisible"}
        if status not in valid_statuses:
            logger.error("Invalid status: %s", status)
            return False
        logger.info("Status update to %s would be sent via gateway", status)
        return True

    async def send_typing(self, channel_id: str) -> bool:
        result = await self._request("POST", f"/channels/{channel_id}/typing")
        return result is not None

    async def get_user_info(self, user_id: str) -> dict[str, Any] | None:
        result = await self._request("GET", f"/users/{user_id}")
        return result if isinstance(result, dict) else None

    async def get_dm_channels(self) -> list[dict[str, Any]]:
        result = await self._request("GET", "/users/@me/channels")
        return result if isinstance(result, list) else []

    async def create_dm(self, recipient_id: str) -> dict[str, Any] | None:
        result = await self._request("POST", "/users/@me/channels", json={"recipient_id": recipient_id})
        return result if isinstance(result, dict) else None

    async def add_reaction(self, channel_id: str, message_id: str, emoji: str) -> bool:
        encoded = requests.utils.quote(emoji)
        result = await self._request(
            "PUT",
            f"/channels/{channel_id}/messages/{message_id}/reactions/{encoded}/@me",
        )
        return result is not None

    async def remove_reaction(self, channel_id: str, message_id: str, emoji: str) -> bool:
        encoded = requests.utils.quote(emoji)
        result = await self._request(
            "DELETE",
            f"/channels/{channel_id}/messages/{message_id}/reactions/{encoded}/@me",
        )
        return result is not None

    async def edit_message(self, channel_id: str, message_id: str, content: str) -> dict[str, Any] | None:
        result = await self._request(
            "PATCH",
            f"/channels/{channel_id}/messages/{message_id}",
            json={"content": content},
        )
        return result if isinstance(result, dict) else None

    async def get_channel(self, channel_id: str) -> dict[str, Any] | None:
        result = await self._request("GET", f"/channels/{channel_id}")
        return result if isinstance(result, dict) else None

    async def get_guild(self, guild_id: str) -> dict[str, Any] | None:
        result = await self._request("GET", f"/guilds/{guild_id}")
        return result if isinstance(result, dict) else None

    async def get_guild_members(self, guild_id: str, limit: int = 100) -> list[dict[str, Any]]:
        result = await self._request("GET", f"/guilds/{guild_id}/members", params={"limit": min(limit, 1000)})
        return result if isinstance(result, list) else []

    async def get_pinned_messages(self, channel_id: str) -> list[dict[str, Any]]:
        result = await self._request("GET", f"/channels/{channel_id}/pins")
        return result if isinstance(result, list) else []

    async def search_messages(self, guild_id: str, query: str, limit: int = 25) -> list[dict[str, Any]]:
        params = {"content": query, "limit": min(limit, 100)}
        result = await self._request("GET", f"/guilds/{guild_id}/messages/search", params=params)
        if isinstance(result, dict):
            return result.get("messages", [])
        return []

    def close(self) -> None:
        if not self._closed:
            self.session.close()
            self._closed = True
            logger.info("Discord client closed")
