"""Voice connection handler for Discord Voice TTS Bot."""

# DEPRECATED: This file is kept for backward compatibility.
# New implementation is in discord_voice_bot.voice package.
# TODO: Remove this file in a future major version.

from typing import TYPE_CHECKING, Any, cast

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
        """
        Initialize the legacy VoiceHandler wrapper and adapt older configuration shapes for the new implementation.

        This constructor normalizes config_manager into a Config dataclass (imported from .config) using the following precedence:
        - If config_manager is already a Config instance, it is used as-is.
        - If config_manager exposes a callable _get_config(), that function is invoked and its result is used; on any exception the fallback Config.from_env() is used.
        - Otherwise Config.from_env() is used.

        The resolved Config and the optional tts_client are forwarded to the new implementation via super().__init__(bot_client, cfg, tts_client).

        Note:
        - tts_client is optional for now but may become required in a future major release.
        - This class is deprecated; prefer discord_voice_bot.voice.VoiceHandler.
        - For backward compatibility this initializer also creates a plain-dict self.stats with keys "messages_processed", "connection_errors", and "tts_messages_played" all initialized to 0.

        """
        # Adapt to new implementation which expects a Config dataclass.
        from .config import Config

        cfg: Config
        if isinstance(config_manager, Config):
            cfg = config_manager
        else:
            getter = getattr(config_manager, "_get_config", None)
            if callable(getter):
                try:
                    cfg = cast(Config, getter())
                except Exception:
                    cfg = Config.from_env()
            else:
                cfg = Config.from_env()

        super().__init__(bot_client, cfg, tts_client)
        logger.warning("⚠️  DEPRECATED: Using old VoiceHandler. Consider migrating to discord_voice_bot.voice.VoiceHandler")

        # Backward-compat: old tests expect a plain dict for stats
        self.stats = {
            "messages_processed": 0,
            "connection_errors": 0,
            "tts_messages_played": 0,
        }

    # All methods are inherited from NewVoiceHandler
    # This class exists only for backward compatibility
