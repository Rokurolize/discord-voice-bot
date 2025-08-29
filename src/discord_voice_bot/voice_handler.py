"""Voice connection handler for Discord Voice TTS Bot."""

# DEPRECATED: This file is kept for backward compatibility.
# New implementation is in discord_voice_bot.voice package.
# TODO: Remove this file in a future major version.

from typing import TYPE_CHECKING, Any

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

    def __init__(self, bot_client: "DiscordVoiceTTSBot", config_manager: Any = None, tts_client: Any | None = None) -> None:
        """Initialize voice handler.

        Args:
            bot_client: The Discord bot client instance
            config_manager: Configuration manager (for compatibility)
            tts_client: Shared TTS client instance. This will become required in a future version.

        """
        # Adapt to new implementation which expects a Config dataclass.
        from .config import Config

        cfg: Config
        if isinstance(config_manager, Config):
            cfg = config_manager
        elif hasattr(config_manager, "_get_config"):
            try:
                cfg = config_manager._get_config()
            except Exception:
                cfg = Config.from_env()
        else:
            cfg = Config.from_env()

        super().__init__(bot_client, cfg)
        logger.warning("⚠️  DEPRECATED: Using old VoiceHandler. Consider migrating to discord_voice_bot.voice.VoiceHandler")

        # Backward-compat: old tests expect a plain dict for stats
        self.stats = {  # type: ignore[assignment]
            "messages_processed": 0,
            "connection_errors": 0,
            "tts_messages_played": 0,
        }

    # All methods are inherited from NewVoiceHandler
    # This class exists only for backward compatibility
