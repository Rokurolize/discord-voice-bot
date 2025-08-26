"""Voice connection handler for Discord Voice TTS Bot."""

# DEPRECATED: This file is kept for backward compatibility.
# New implementation is in discord_voice_bot.voice package.
# TODO: Remove this file in a future major version.

from typing import TYPE_CHECKING, Any

from loguru import logger

if TYPE_CHECKING:
    from .bot import DiscordVoiceTTSBot

# Import new implementation
from .tts_client import TTSClient
from .voice import VoiceHandler as NewVoiceHandler


class VoiceHandler(NewVoiceHandler):
    """Manages Discord voice connections and audio playback.

    DEPRECATED: This class is kept for backward compatibility.
    Use discord_voice_bot.voice.VoiceHandler instead.
    """

    def __init__(self, bot_client: "DiscordVoiceTTSBot", config_manager: Any = None, tts_client: TTSClient | None = None) -> None:
        """Initialize voice handler.

        Args:
            bot_client: The Discord bot client instance
            config_manager: Configuration manager (for compatibility)
            tts_client: Shared TTS client instance

        """
        # Delegate to new implementation - config_manager is always passed from factory
        if tts_client is None:
            from .config_manager import ConfigManagerImpl

            # If no tts_client is provided, create a temporary one for backward compatibility
            config = config_manager or ConfigManagerImpl()
            tts_client = TTSClient(config)
            logger.warning("⚠️  DEPRECATED: Creating temporary TTSClient for old VoiceHandler. Please update to inject it.")

        super().__init__(bot_client, config_manager, tts_client)
        logger.warning("⚠️  DEPRECATED: Using old VoiceHandler. Consider migrating to discord_voice_bot.voice.VoiceHandler")

    # All methods are inherited from NewVoiceHandler
    # This class exists only for backward compatibility
