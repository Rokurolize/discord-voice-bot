"""Voice connection handler for Discord Voice TTS Bot."""

# DEPRECATED: This file is kept for backward compatibility.
# New implementation is in discord_voice_bot.voice package.
# TODO: Remove this file in a future major version.

from typing import TYPE_CHECKING

from loguru import logger

if TYPE_CHECKING:
    from .bot import DiscordVoiceTTSBot

# Import new implementation
from .voice import VoiceHandler as NewVoiceHandler


class VoiceHandler(NewVoiceHandler):
    """Manages Discord voice connections and audio playback.

    DEPRECATED: This class is kept for backward compatibility.
    Use discord_voice_bot.voice.VoiceHandler instead.
    """

    def __init__(self, bot_client: "DiscordVoiceTTSBot"):
        """Initialize voice handler.

        Args:
            bot_client: The Discord bot client instance

        """
        # Delegate to new implementation
        super().__init__(bot_client)
        logger.warning("⚠️  DEPRECATED: Using old VoiceHandler. Consider migrating to discord_voice_bot.voice.VoiceHandler")

    # All methods are inherited from NewVoiceHandler
    # This class exists only for backward compatibility
