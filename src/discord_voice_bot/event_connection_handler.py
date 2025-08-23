"""Connection handling for event handler."""

import asyncio
from typing import TYPE_CHECKING, Any

import discord
from loguru import logger

if TYPE_CHECKING:
    from .protocols import ConfigManager, DiscordVoiceBotTTS


class ConnectionHandler:
    """Handles voice connection events and reconnection logic."""

    def __init__(self, bot: "DiscordVoiceBotTTS", config_manager: "ConfigManager"):
        """Initialize connection handler."""
        super().__init__()
        self.bot = bot
        self._config_manager = config_manager
        self._voice_state_updating = False
        self.target_channel_id: int = 0

    async def handle_voice_state_update(
        self,
        member: discord.Member,
        before: discord.VoiceState,
        after: discord.VoiceState,
    ) -> None:
        """Handle voice state update events with improved reconnection logic."""
        try:
            # Ensure we are handling a voice state update for the bot itself
            if not self.bot.user or member.id != self.bot.user.id:
                return

            before_channel_name = before.channel.name if before.channel else "None"
            after_channel_name = after.channel.name if after.channel else "None"
            logger.debug(f"Voice state update - Before: {before_channel_name}, After: {after_channel_name}")

            # If the bot is disconnected from a voice channel, attempt to reconnect
            if before.channel and not after.channel:
                logger.warning(f"⚠️ VOICE DISCONNECTION DETECTED - Bot was disconnected from {before_channel_name} (ID: {before.channel.id})")

                # Report disconnection to health monitor
                if hasattr(self.bot, "health_monitor") and self.bot.health_monitor:
                    self.bot.health_monitor.record_disconnection(f"Disconnected from {before_channel_name}")

                # Check if we're already attempting reconnection
                if self._voice_state_updating:
                    logger.debug("Reconnection already in progress, skipping")
                    return

                # Always attempt cleanup first
                if hasattr(self.bot, "voice_handler") and self.bot.voice_handler:
                    await self.bot.voice_handler.cleanup_voice_client()

                # Only reconnect if the voice handler is initialized
                if hasattr(self.bot, "voice_handler") and self.bot.voice_handler:
                    self._voice_state_updating = True
                    try:
                        # Add a longer delay to prevent rapid reconnection loops
                        await asyncio.sleep(5)
                        logger.info(f"🔄 ATTEMPTING RECONNECTION to voice channel {self.target_channel_id}")

                        # Force cleanup before attempting new connection
                        await self.bot.voice_handler.cleanup_voice_client()

                        success = await self.bot.voice_handler.connect_to_channel(self.target_channel_id)
                        if success:
                            logger.info("✅ SUCCESSFULLY RECONNECTED to voice channel")
                        else:
                            logger.error("❌ RECONNECTION FAILED - Will retry on next voice state update")
                    except Exception as e:
                        logger.error(f"💥 CRITICAL ERROR during reconnection attempt: {e}")
                    finally:
                        self._voice_state_updating = False
                else:
                    logger.warning("Voice handler not initialized - cannot reconnect")

        except Exception as e:
            logger.error(f"💥 CRITICAL ERROR handling voice state update: {e!s}")
            self._voice_state_updating = False  # Reset flag on error

    async def handle_disconnect(self) -> None:
        """Handle bot disconnect."""
        logger.warning("Bot disconnected from Discord - monitoring for reconnection")
        logger.debug("Setting startup_complete to False due to disconnect")
        self.bot.startup_complete = False

        # Log additional context if available
        if hasattr(self.bot, "voice_handler") and self.bot.voice_handler:
            voice_status = self.bot.voice_handler.get_status()
            logger.debug(f"Voice handler status at disconnect: {voice_status}")

    async def handle_resumed(self) -> None:
        """Handle bot resume."""
        logger.info("Bot connection resumed")

    async def handle_voice_server_update(self, payload: dict[str, Any]) -> None:
        """Handle VOICE_SERVER_UPDATE event with proper Discord API compliance."""
        if hasattr(self.bot, "voice_handler") and self.bot.voice_handler:
            await self.bot.voice_handler.handle_voice_server_update(payload)
        else:
            logger.warning("⚠️ Voice handler not initialized, cannot handle voice server update")

    async def handle_error(self, event: str, *args: Any, **kwargs: Any) -> None:
        """Handle general errors."""
        logger.error(f"Discord event error in {event}: {args} {kwargs}")

    def set_target_channel_id(self, channel_id: int) -> None:
        """Set the target voice channel ID."""
        self.target_channel_id = channel_id
