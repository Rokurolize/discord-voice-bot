"""Voice connection management for voice handler."""

import asyncio
from typing import Any

import discord
from loguru import logger

from ..protocols import ConfigManager


class VoiceConnectionManager:
    """Manages Discord voice connections and related functionality."""

    def __init__(self, bot_client: discord.Client, config_manager: ConfigManager) -> None:
        """Initialize voice connection manager."""
        super().__init__()
        self.bot = bot_client
        self._config_manager = config_manager
        self.voice_client: discord.VoiceClient | None = None
        self.voice_gateway = None
        self.target_channel: discord.VoiceChannel | discord.StageChannel | None = None
        self.connection_state = "DISCONNECTED"
        self._last_connection_attempt = 0.0
        self._reconnection_cooldown = 5  # seconds

        # Initialize voice gateway for backward compatibility
        from .gateway import VoiceGatewayManager

        # Initialize with None for now, will be set when voice client is available
        self.voice_gateway = VoiceGatewayManager(None)  # type: ignore[arg-type]

    async def connect_to_channel(self, channel_id: int) -> bool:
        """Connect to a voice channel with comprehensive error handling."""
        try:
            # Check reconnection cooldown
            now = asyncio.get_running_loop().time()
            time_since_last_attempt = now - self._last_connection_attempt
            if time_since_last_attempt < self._reconnection_cooldown:
                wait_time = self._reconnection_cooldown - time_since_last_attempt
                logger.debug(f"⏳ Respecting reconnection cooldown: waiting {wait_time:.1f}s")
                await asyncio.sleep(wait_time)

            self._last_connection_attempt = now
            logger.info(f"🔄 ATTEMPTING VOICE CONNECTION - Channel ID: {channel_id}")

            # Get channel information
            channel = self.bot.get_channel(channel_id)
            if not channel:
                logger.error(f"❌ CHANNEL NOT FOUND - Channel {channel_id} does not exist or is not accessible")
                return False

            if not isinstance(channel, (discord.VoiceChannel, discord.StageChannel)):
                logger.error(f"❌ INVALID CHANNEL TYPE - Channel {channel_id} is not a voice channel")
                return False

            logger.info(f"📍 TARGET CHANNEL INFO - Name: {channel.name}, Type: {type(channel).__name__}, Guild: {channel.guild.name}")

            # Check current connection status
            if self.is_connected():
                current_channel_id = getattr(self.voice_client.channel, "id", None) if self.voice_client else None

                if current_channel_id == channel_id:
                    logger.info(f"✅ ALREADY CONNECTED - Already connected to target channel {channel.name}")
                    return True
                else:
                    if self.voice_client and self.voice_client.channel:
                        logger.info(f"🔄 MOVING CHANNELS - From {self.voice_client.channel.name} to {channel.name}")
                    try:
                        if self.voice_client:
                            await self.voice_client.move_to(channel)
                            logger.info(f"✅ SUCCESSFULLY MOVED - Now connected to voice channel: {channel.name}")
                            return True
                    except Exception as move_error:
                        logger.error(f"❌ MOVE FAILED - Error moving to channel {channel.name}: {move_error}")
                        if self.voice_client:
                            await self.voice_client.disconnect()
                            self.voice_client = None

            # Fresh connection attempt
            logger.info(f"🔗 ESTABLISHING NEW CONNECTION - Connecting to {channel.name}")
            self.voice_client = await channel.connect()
            logger.info(f"✅ CONNECTION SUCCESSFUL - Connected to voice channel: {channel.name}")

            # Initialize voice gateway manager
            if self.voice_client:
                from .gateway import VoiceGatewayManager

                self.voice_gateway = VoiceGatewayManager(self.voice_client)
                logger.info("🎯 Voice Gateway Manager initialized")

            # Verify connection
            await asyncio.sleep(0.5)
            if not self.is_connected():
                logger.warning("⚠️ CONNECTION UNSTABLE - Discord immediately disconnected")
                return False

            # Handle stage channel specifics
            if isinstance(channel, discord.StageChannel):
                await asyncio.sleep(1)
                if channel.guild.me and channel.guild.me.voice and channel.guild.me.voice.suppress:
                    try:
                        _ = await channel.guild.me.edit(suppress=False)
                        logger.info("🎤 STAGE CHANNEL - Successfully requested to speak")
                    except Exception as stage_error:
                        logger.warning(f"⚠️ STAGE CHANNEL - Failed to request speaking: {stage_error}")

            return True

        except Exception as e:
            logger.error(f"❌ CRITICAL CONNECTION FAILURE - Failed to connect to voice channel {channel_id}: {e}")
            await self.cleanup_voice_client()
            return False

    async def handle_voice_server_update(self, payload: dict[str, Any]) -> None:
        """Handle VOICE_SERVER_UPDATE event."""
        if self.voice_gateway:
            await self.voice_gateway.handle_voice_server_update(payload)
        else:
            logger.warning("⚠️ Voice gateway manager not initialized, cannot handle voice server update")

    async def handle_voice_state_update(self, payload: dict[str, Any]) -> None:
        """Handle VOICE_STATE_UPDATE event."""
        if self.voice_gateway:
            await self.voice_gateway.handle_voice_state_update(payload)
        else:
            logger.warning("⚠️ Voice gateway manager not initialized, cannot handle voice state update")

    def is_connected(self) -> bool:
        """Check if the bot is connected to a voice channel."""
        try:
            return self.voice_client is not None and self.voice_client.is_connected()
        except Exception:
            return False

    async def cleanup_voice_client(self) -> None:
        """Aggressively clean up voice client state."""
        if not self.voice_client:
            return

        logger.debug("🧹 Cleaning up voice client...")

        try:
            if hasattr(self.voice_client, "is_connected") and self.voice_client.is_connected():
                await self.voice_client.disconnect()
                logger.debug("✅ Voice client disconnected gracefully")
            else:
                logger.debug("ℹ️ Voice client was already disconnected")
        except Exception as e:
            logger.warning(f"⚠️ Error during graceful disconnect: {e}")

        try:
            self.voice_client = None
            logger.debug("✅ Voice client reference cleared")
        except Exception as e:
            logger.error(f"💥 Error clearing voice client reference: {e}")

        self.connection_state = "DISCONNECTED"

    def get_connection_info(self) -> dict[str, Any]:
        """Get current connection information."""
        connected = bool(self.voice_client and self.voice_client.is_connected())
        channel_name = None
        channel_id = None

        try:
            if self.voice_client and getattr(self.voice_client, "channel", None):
                channel_name = self.voice_client.channel.name
                channel_id = self.voice_client.channel.id
            elif self.target_channel:
                channel_name = self.target_channel.name
                channel_id = self.target_channel.id
        except Exception:
            pass

        return {"connected": connected, "channel_name": channel_name, "channel_id": channel_id, "connection_state": self.connection_state}

    @property
    def last_connection_attempt(self) -> float:
        """Get the timestamp of the last connection attempt."""
        return self._last_connection_attempt

    @last_connection_attempt.setter
    def last_connection_attempt(self, value: float) -> None:
        """Set timestamp of the last connection attempt (seconds from asyncio loop's monotonic clock)."""
        try:
            self._last_connection_attempt = float(value)
        except (TypeError, ValueError) as e:
            raise TypeError("last_connection_attempt must be a float-like value.") from e

    @property
    def reconnection_cooldown(self) -> int:
        """Get the reconnection cooldown duration in seconds."""
        return self._reconnection_cooldown

    @reconnection_cooldown.setter
    def reconnection_cooldown(self, value: int) -> None:
        """Set the reconnection cooldown duration in seconds."""
        if value < 0:
            raise ValueError("reconnection_cooldown must be non-negative")
        self._reconnection_cooldown = int(value)
