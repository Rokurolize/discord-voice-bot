"""Voice gateway connection manager for Discord Voice TTS Bot."""

from typing import Any

import discord
from loguru import logger


class VoiceGatewayManager:
    """Manages voice gateway connections following Discord's official steps."""

    def __init__(self, voice_client: discord.VoiceClient):
        super().__init__()
        self.voice_client = voice_client
        self._session_id: str | None = None
        self._token: str | None = None
        self._endpoint: str | None = None
        self._guild_id: int | None = None
        self._connected = False

    async def handle_voice_server_update(self, payload: dict[str, Any]) -> None:
        """Handle VOICE_SERVER_UPDATE event following Discord's official steps."""
        try:
            self._token = payload.get("token")
            self._guild_id = payload.get("guild_id")
            self._endpoint = payload.get("endpoint")

            # Remove protocol if present and add voice gateway version
            if self._endpoint and "://" in self._endpoint:
                self._endpoint = self._endpoint.split("://")[1]

            logger.info(f"📡 Voice server update received - Guild: {self._guild_id}, Endpoint: {self._endpoint}")

            # The voice client handles the connection internally, but we ensure proper setup
            await self._ensure_proper_voice_setup()

        except Exception as e:
            logger.error(f"❌ Error handling voice server update: {e}")

    async def handle_voice_state_update(self, payload: dict[str, Any]) -> None:
        """Handle VOICE_STATE_UPDATE event."""
        try:
            self._session_id = payload.get("session_id")
            logger.info(f"🎤 Voice state update - Session ID: {self._session_id}")

            # Voice client handles the connection, but we track state for compliance
            if self._session_id and self.voice_client.is_connected():
                self._connected = True
                logger.info("✅ Voice gateway connection established with proper session")

        except Exception as e:
            logger.error(f"❌ Error handling voice state update: {e}")

    async def _ensure_proper_voice_setup(self) -> None:
        """Ensure voice connection follows Discord's official patterns."""
        try:
            # Discord.py handles most of the voice gateway internally
            # We focus on ensuring proper state and logging compliance

            # Verify connection state
            if self.voice_client.is_connected():
                logger.info("✅ Voice client connected with Discord API compliance")
                self._connected = True

                # Log connection details for transparency
                if hasattr(self.voice_client, "channel") and self.voice_client.channel:
                    logger.debug(f"🎵 Connected to voice channel: {self.voice_client.channel.name}")
                    logger.debug(f"🔊 Voice client SSRC: {getattr(self.voice_client, 'ssrc', 'Unknown')}")
            else:
                logger.warning("⚠️ Voice client not yet connected, waiting for handshake completion")

        except Exception as e:
            logger.error(f"❌ Error in voice setup validation: {e}")

    def get_connection_info(self) -> dict[str, Any]:
        """Get voice connection information for debugging."""
        return {
            "connected": self._connected,
            "session_id": self._session_id,
            "guild_id": self._guild_id,
            "has_token": self._token is not None,
            "endpoint": self._endpoint,
            "client_connected": self.voice_client.is_connected() if self.voice_client else False,
        }

    def is_connected(self) -> bool:
        """Check if voice gateway connection is established."""
        return self._connected and self.voice_client.is_connected()
