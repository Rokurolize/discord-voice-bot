"""Voice connection management for voice handler."""

import asyncio
from typing import Any, cast

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
        """
        Attempt to connect the bot to a Discord voice or stage channel.

        This method respects the reconnection cooldown and updates the manager's
        last_connection_attempt. If already connected it will move the existing
        voice client to the target channel; otherwise it creates a new connection,
        initializes the VoiceGatewayManager, verifies the connection, and for
        StageChannels attempts to request speaking. On transient failures the
        voice client is cleaned up.

        Args:
            channel_id: Discord ID of the target voice or stage channel.

        Returns:
            bool: True when connected to (or moved to) the target channel and the
            connection is verified; False on failure.

        Raises:
            asyncio.CancelledError: Propagated to allow callers to handle cancellations/timeouts.

        """
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
                        # Use unified cleanup path to ensure consistent teardown
                        await self.cleanup_voice_client()

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

        except asyncio.CancelledError:
            # Propagate cancellation so callers (e.g., slash handler) can handle timeouts
            raise
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
            # Prefer current voice_client if available
            if self.voice_client is not None:
                return self.voice_client.is_connected()

            # Fallback: if we know the target channel, ask the guild for its voice_client
            if self.target_channel is not None:
                vc = cast(discord.VoiceClient | None, self.target_channel.guild.voice_client)
                return bool(vc and getattr(vc, "is_connected", lambda: False)())

            # Last resort: inspect any active voice_clients on the bot
            if hasattr(self.bot, "voice_clients"):
                for vc in getattr(self.bot, "voice_clients"):
                    if vc and getattr(vc, "is_connected", lambda: False)():
                        return True
            return False
        except Exception:
            return False

    async def cleanup_voice_client(self) -> None:
        """Aggressively clean up voice client state."""
        if not self.voice_client:
            return

        logger.debug("🧹 Cleaning up voice client...")

        try:
            if hasattr(self.voice_client, "is_connected") and self.voice_client.is_connected():
                try:
                    await asyncio.wait_for(self.voice_client.disconnect(), timeout=5.0)
                    logger.debug("✅ Voice client disconnected gracefully")
                except TimeoutError:
                    logger.warning("⚠️ Voice client disconnect timed out after 5s; attempting retries and forced cleanup")
                    # Short retry sequence with smaller timeouts, then force cleanup
                    for i in range(2):
                        try:
                            await asyncio.wait_for(self.voice_client.disconnect(), timeout=2.0)
                            logger.debug("✅ Voice client disconnected on retry #%d", i + 1)
                            break
                        except TimeoutError:
                            continue
                        except Exception as e2:
                            logger.warning(f"⚠️ Error during disconnect retry: {e2}")
                            break
                    else:
                        # Last resort: try best-effort attribute-level close/cleanup if present
                        try:
                            closer = getattr(self.voice_client, "close", None)
                            if callable(closer):
                                await asyncio.wait_for(closer(), timeout=2.0) if asyncio.iscoroutinefunction(closer) else closer()
                        except Exception as e3:
                            logger.warning(f"⚠️ Force cleanup encountered an error: {e3}")
                except asyncio.CancelledError:
                    # Propagate cancellation
                    raise
                except Exception as e:
                    logger.warning(f"⚠️ Error during graceful disconnect: {e}")
            else:
                logger.debug("ℹ️ Voice client was already disconnected")
        except asyncio.CancelledError:
            # Preserve cooperative cancellation
            raise
        except Exception as e:
            logger.warning(f"⚠️ Error during voice client cleanup: {e}")

        try:
            self.voice_client = None
            logger.debug("✅ Voice client reference cleared")
        except Exception as e:
            logger.error(f"💥 Error clearing voice client reference: {e}")

        self.connection_state = "DISCONNECTED"

    def get_connection_info(self) -> dict[str, Any]:
        """Get current connection information."""
        connected = self.is_connected()
        channel_name = None
        channel_id = None

        try:
            vc = self.voice_client
            if not vc and self.target_channel is not None:
                vc = cast(discord.VoiceClient | None, self.target_channel.guild.voice_client)
            if vc and getattr(vc, "channel", None):
                ch = cast(Any, vc.channel)
                channel_name = cast(str, getattr(ch, "name", None))
                channel_id = cast(int, getattr(ch, "id", None))
            elif self.target_channel:
                channel_name = self.target_channel.name
                channel_id = self.target_channel.id
        except Exception:
            pass

        return {"connected": connected, "channel_name": channel_name, "channel_id": channel_id, "connection_state": self.connection_state}

    @property
    def last_connection_attempt(self) -> float:
        """
        Return the monotonic timestamp of the last attempt to (re)connect the voice client.

        The value is taken from the running event loop's time source and is intended for
        calculating reconnection cooldowns; callers should treat it as a monotonic
        float (seconds).
        """
        return self._last_connection_attempt

    @last_connection_attempt.setter
    def last_connection_attempt(self, value: float) -> None:
        """
        Set the timestamp of the last connection attempt.

        Args:
            value: Float-like seconds from the asyncio loop's monotonic clock; will be coerced to float.

        Raises:
            TypeError: If `value` cannot be converted to float.

        """
        try:
            self._last_connection_attempt = float(value)
        except (TypeError, ValueError) as e:
            raise TypeError("last_connection_attempt must be a float-like value.") from e

    @property
    def reconnection_cooldown(self) -> int:
        """
        Return the reconnection cooldown in seconds.

        This is a non-negative integer representing how long to wait between
        connection attempts (in seconds). The corresponding setter coerces values
        to int and enforces non-negativity.
        """
        return self._reconnection_cooldown

    @reconnection_cooldown.setter
    def reconnection_cooldown(self, value: int) -> None:
        """
        Set the reconnection cooldown duration, in seconds.

        Accepts an int-like value which will be coerced to int and stored as the internal cooldown.
        Raises a TypeError if the value cannot be converted to int, and a ValueError if the resulting
        integer is negative.

        Args:
            value: Non-negative number of seconds to wait between reconnection attempts.

        """
        try:
            ivalue = int(value)
        except (TypeError, ValueError) as e:
            raise TypeError("reconnection_cooldown must be an int-like value.") from e
        if ivalue < 0:
            raise ValueError("reconnection_cooldown must be non-negative")
        self._reconnection_cooldown = ivalue
