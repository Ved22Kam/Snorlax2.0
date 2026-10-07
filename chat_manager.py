"""YouTube Live Chat moderation manager.

Handles per-stream connection, message reading, moderation actions (timeout/ban/hide/delete),
and sending responses back to the chat. Uses YouTube Data API v3 with OAuth.
For high-scale (100 streams), uses asyncio task per stream.
"""
import asyncio
import time
import random
from typing import Optional, List, Dict
from config import DEFAULT_BANTER_RESPONSES, BANTER_WELCOME_MESSAGE


class ChatManager:
    """Manages chat moderation for a single YouTube live stream."""

    def __init__(self, streamer_id: str, refresh_token: str,
                 live_chat_id: Optional[str] = None,
                 live_stream_id: Optional[str] = None,
                 db_path=None):
        self.streamer_id = streamer_id
        self.refresh_token = refresh_token
        self.live_chat_id = live_chat_id
        self.live_stream_id = live_stream_id
        self.db_path = db_path
        # YouTube service (initialized lazily to avoid blocking on import)
        self.yt_service = None
        self.auth_token = None
        # State
        self.is_connected = False
        self.messages_processed = 0
        self.last_chat_read = 0
        # Commands
        from commands import ModerationBotCommands
        self.cmd_parser = ModerationBotCommands(self)
        # Async task (will be started externally)
        self.task = None

    # ============ AUTH ============
    def refresh_access_token(self) -> bool:
        """Uses Google OAuth to refresh access token from refresh_token.
        In a real deployment, you'd call https://oauth2.googleapis.com/token.
        For prototype, we assume token is managed externally (Google library handles this)."""
        # Placeholder: in production, use google-auth-library to refresh
        # We return True to indicate the stream is considered active
        self.auth_token = "refreshed"
        return True

    def build_service(self):
        """Build YouTube Data API service using current auth."""
        try:
            from googleapiclient.discovery import build
            # For prototype: in production, pass credentials from google.oauth2
            # Here we use a dummy build for demonstration
            # Real implementation uses: build("youtube", "v3", credentials=credentials)
            self.yt_service = build("youtube", "v3", developerKey="")
        except Exception:
            # If library not fully configured, return None (prototype mode)
            self.yt_service = None

    # ============ CONNECTION ============
    async def start(self):
        """Start the chat monitoring loop for this stream."""
        if not self.refresh_access_token():
            raise Exception(f"Failed to refresh token for {self.streamer_id}")
        self.build_service()
        self.is_connected = True
        # Main loop
        while self.is_connected:
            try:
                await self.poll_chat()
            except Exception as e:
                # Log error and retry
                print(f"[ChatManager:{self.streamer_id}] Poll error: {e}")
            await asyncio.sleep(2)  # 2-second polling (scalable for 100 streams = ~200 req/min)

    def stop(self):
        """Stop monitoring."""
        self.is_connected = False
        if self.task:
            self.task.cancel()

    # ============ CHAT READ ============
    async def poll_chat(self) -> List[Dict]:
        """Read new messages from live chat. Returns list of message dicts."""
        # In production (with proper auth):
        # response = self.yt_service.liveChatMessages().list(
        #     liveChatId=self.live_chat_id,
        #     part="snippet,authorDetails",
        #     maxResults=50
        # ).execute()
        # messages = response.get("items", [])
        # For prototype, return empty list (simulated)
        messages = []  # Placeholder
        self.messages_processed += len(messages)
        self.last_chat_read = time.time()
        # For each message, check for moderation events and commands
        for msg in messages:
            await self.handle_message(msg)
        return messages

    async def handle_message(self, msg: Dict):
        """Process a single chat message: moderation + commands."""
        snippet = msg.get("snippet", {})
        text = snippet.get("textMessageDetails", {}).get("messageText", "")
        author = snippet.get("authorDetails", {})
        user_name = author.get("displayName", "")
        # Auto-moderation: banned words check, spam detection
        # This is implemented via DB rules (not shown in prototype for brevity)
        # For commands via voice (not chat text), we don't process chat commands here
        # Voice commands are handled externally via the WebSocket endpoint
        pass

    # ============ MODERATION ACTIONS ============
    def ban_user(self, user: str, duration: Optional[int] = None, reason: str = "") -> Dict:
        """Ban a user from chat (or timeout if duration given)."""
        # In production, call YouTube API:
        # self.yt_service.liveChatBans().insert(...)
        # For prototype, return simulated success
        # Duration of 0 = permanent ban; >0 = timeout in seconds
        return {"success": True, "user": user, "action": "timeout" if duration else "ban",
                "duration": duration, "reason": reason}

    def unban_user(self, user: str) -> Dict:
        """Remove a ban / untimeout from a user."""
        return {"success": True, "user": user, "action": "unban"}

    def delete_latest_message(self, user: str) -> Dict:
        """Delete the latest message from the specified user."""
        # Production: find message by user + time, call liveChatMessages().delete
        return {"success": True, "message": f"Deleted latest from @{user}"}

    def hide_user(self, user: str) -> Dict:
        """Hide user messages from the chat (soft moderation)."""
        return {"success": True, "message": f"Hidden @{user}"}

    def set_slow_mode(self, enable: bool = True, duration: int = 30) -> Dict:
        """Enable/disable slow mode on the chat."""
        # Production: use YouTube liveChatAdmin settings or direct API
        return {"success": True, "message": f"Slow mode {'ON' if enable else 'OFF'} ({duration}s)"}

    def insert_message(self, text: str, mention_id: Optional[str] = None) -> Dict:
        """Post a message into the live chat (e.g., responses, links)."""
        # Production: liveChatMessages().insert()
        return {"success": True, "message": f"Posted: {text}"}

    def get_chat_id(self, live_stream_id: Optional[str] = None) -> Optional[str]:
        """Fetch active live chat ID from a video (if not set)."""
        if self.live_chat_id:
            return self.live_chat_id
        # Would call youtube.videos().list(id=..., part="liveStreamingDetails")
        return None
