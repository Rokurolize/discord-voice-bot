"""Configuration manager to eliminate circular imports."""

from typing import Any, override

from .config import get_config
from .protocols import ConfigManager


class ConfigManagerImpl(ConfigManager):
    """Configuration manager implementation that wraps the existing Config class."""

    def __init__(self) -> None:
        """Initialize configuration manager."""
        super().__init__()
        # Delay config creation until first access to avoid circular imports
        self._config: Any = None  # TODO: Replace with proper Config type

    def _get_config(self) -> Any:
        """Get configuration instance, creating it if necessary."""
        if self._config is None:
            self._config = get_config()
        return self._config

    @override
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value by key."""
        config = self._get_config()
        return getattr(config, key, default)

    @override
    def get_api_url(self) -> str:
        """Get TTS API URL."""
        return self._get_config().api_url

    @override
    def get_speaker_id(self) -> int:
        """Get default speaker ID."""
        return self._get_config().speaker_id

    @override
    def get_tts_engine(self) -> str:
        """Get TTS engine name."""
        return self._get_config().tts_engine

    @override
    def get_audio_sample_rate(self) -> int:
        """Get audio sample rate."""
        return self._get_config().audio_sample_rate

    @override
    def get_audio_channels(self) -> int:
        """Get audio channels."""
        return self._get_config().audio_channels

    @override
    def get_log_level(self) -> str:
        """Get logging level."""
        return self._get_config().log_level

    @override
    def validate(self) -> None:
        """Validate configuration."""
        self._get_config().validate()

    # Additional convenience methods for specific config access
    @override
    def get_discord_token(self) -> str:
        """Get Discord bot token."""
        return self._get_config().discord_token

    @override
    def get_target_guild_id(self) -> int:
        """Get target guild ID."""
        return self._get_config().target_guild_id

    @override
    def get_target_voice_channel_id(self) -> int:
        """Get target voice channel ID."""
        return self._get_config().target_voice_channel_id

    @override
    def get_command_prefix(self) -> str:
        """Get command prefix."""
        return self._get_config().command_prefix

    @override
    def get_engine_config(self) -> dict[str, Any]:
        """Get current TTS engine configuration."""
        return self._get_config().engine_config

    @override
    def get_engines(self) -> dict[str, dict[str, Any]]:
        """Get all engine configurations."""
        return self._get_config().engines

    @override
    def get_max_message_length(self) -> int:
        """Get maximum message length."""
        return self._get_config().max_message_length

    @override
    def get_message_queue_size(self) -> int:
        """Get message queue size."""
        return self._get_config().message_queue_size

    @override
    def get_reconnect_delay(self) -> int:
        """Get reconnect delay."""
        return self._get_config().reconnect_delay

    @override
    def get_rate_limit_messages(self) -> int:
        """Get rate limit messages."""
        return self._get_config().rate_limit_messages

    @override
    def get_rate_limit_period(self) -> int:
        """Get rate limit period."""
        return self._get_config().rate_limit_period

    @override
    def get_log_file(self) -> str | None:
        """Get log file path."""
        return self._get_config().log_file

    @override
    def is_debug(self) -> bool:
        """Check if debug mode is enabled."""
        return self._get_config().debug

    @override
    def get_intents(self) -> Any:
        """Get Discord intents."""
        return self._get_config().get_intents()

    @override
    def get_enable_self_message_processing(self) -> bool:
        """Check if self-message processing is enabled."""
        return self._get_config().enable_self_message_processing
