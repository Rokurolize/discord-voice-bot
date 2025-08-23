"""Discord event handling for Voice TTS Bot."""

from typing import TYPE_CHECKING, Any

import discord
from loguru import logger

# Import new manager classes
from .event_connection_handler import ConnectionHandler
from .event_message_handler import MessageHandler
from .event_startup_manager import StartupManager

if TYPE_CHECKING:
    from .protocols import ConfigManager, DiscordVoiceBotTTS


class EventHandler:
    """Handles Discord events using facade pattern with specialized managers."""

    def __init__(self, bot: "DiscordVoiceBotTTS", config_manager: "ConfigManager"):
        """Initialize event handler with manager components.

        Args:
            bot: The Discord bot instance with required components
            config_manager: Configuration manager instance

        """
        super().__init__()
        self.bot = bot
        self._config_manager = config_manager

        # Initialize manager components
        self.startup_manager = StartupManager(bot, config_manager)
        self.message_handler = MessageHandler(bot, config_manager)
        self.connection_handler = ConnectionHandler(bot, config_manager)

        # Set target channel ID in connection handler
        self.target_channel_id = self._config_manager.get_target_voice_channel_id()
        self.connection_handler.set_target_channel_id(self.target_channel_id)

        logger.info("Event handler initialized with manager components")

    async def handle_ready(self) -> None:
        """Handle bot ready event using startup manager."""
        await self.startup_manager.handle_startup()

    async def handle_message(self, message: discord.Message) -> None:
        """Handle message events using message handler."""
        await self.message_handler.handle_message(message)

    async def handle_voice_state_update(
        self,
        member: discord.Member,
        before: discord.VoiceState,
        after: discord.VoiceState,
    ) -> None:
        """Handle voice state update events using connection handler."""
        await self.connection_handler.handle_voice_state_update(member, before, after)

    async def handle_disconnect(self) -> None:
        """Handle bot disconnect using connection handler."""
        await self.connection_handler.handle_disconnect()

    async def handle_resumed(self) -> None:
        """Handle bot resume using connection handler."""
        await self.connection_handler.handle_resumed()

    async def handle_voice_server_update(self, payload: dict[str, Any]) -> None:
        """Handle VOICE_SERVER_UPDATE event using connection handler."""
        await self.connection_handler.handle_voice_server_update(payload)

    async def handle_error(self, event: str, *args: Any, **kwargs: Any) -> None:
        """Handle general errors using connection handler."""
        await self.connection_handler.handle_error(event, *args, **kwargs)
