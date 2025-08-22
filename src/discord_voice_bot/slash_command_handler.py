"""Slash command handling for Discord Voice TTS Bot."""

# DEPRECATED: This file is kept for backward compatibility.
# New implementation is in discord_voice_bot.slash package.
# TODO: Remove this file in a future major version.

from typing import TYPE_CHECKING

from loguru import logger

if TYPE_CHECKING:
    from .bot import DiscordVoiceTTSBot

# Import new implementation
from .slash import SlashCommandHandler as NewSlashCommandHandler


class SlashCommandHandler(NewSlashCommandHandler):
    """Handles Discord slash commands with modern app command framework.

    DEPRECATED: This class is kept for backward compatibility.
    Use discord_voice_bot.slash.SlashCommandHandler instead.
    """

    def __init__(self, bot: "DiscordVoiceTTSBot"):
        """Initialize slash command handler.

        Args:
            bot: The Discord bot instance

        """
        # Delegate to new implementation
        super().__init__(bot)
        logger.warning("⚠️  DEPRECATED: Using old SlashCommandHandler. Consider migrating to discord_voice_bot.slash.SlashCommandHandler")

    # All methods are inherited from NewSlashCommandHandler
    # This class exists only for backward compatibility
