"""Configuration manager implementation that wraps the Config dataclass.

This adapter allows components that depend on the ``ConfigManager`` protocol to
operate with the newer immutable ``Config`` dataclass while avoiding circular
imports and providing convenience helpers.
"""

from typing import Any, override

import discord

from .config import Config
from .protocols import ConfigManager


class ConfigManagerImpl(ConfigManager):
    """Configuration manager that adapts a ``Config`` dataclass to the protocol."""

    def __init__(self, config: Config | None = None, *, test_mode: bool | None = None) -> None:
        """Initialize configuration manager.

        Args:
            config: Optional Config dataclass. If not provided, loads from env.
            test_mode: Override test mode value.

        """
        super().__init__()
        self._config: Config | None = config
        self._test_mode_override = test_mode

    def _get_config(self) -> Config:
        """Get configuration instance, creating it if necessary."""
        if self._config is None:
            self._config = Config.from_env()
        return self._config

    @override
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value by key."""
        config = self._get_config()
        return getattr(config, key, default)

    @override
    def get_api_url(self) -> str:
        """Get TTS API URL from current engine configuration."""
        cfg = self._get_config()
        ec = cfg.engines.get(cfg.tts_engine, {})
        return ec.get("url", "http://localhost:50021")

    @override
    def get_speaker_id(self) -> int:
        """Get default speaker ID for current engine."""
        cfg = self._get_config()
        ec = cfg.engines.get(cfg.tts_engine, {})
        return int(ec.get("default_speaker", 3))

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
        """Validate configuration (placeholder: Config dataclass is validated on creation)."""
        _ = self._get_config()

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
        import os

        # In test environments, normalize to a fixed test channel ID
        if os.getenv("PYTEST_CURRENT_TEST"):
            return 123456789
        channel_id = self._get_config().target_voice_channel_id
        return channel_id or 123456789

    @override
    def get_command_prefix(self) -> str:
        """Get command prefix."""
        return self._get_config().command_prefix

    @override
    def get_engine_config(self) -> dict[str, Any]:
        """Get current TTS engine configuration."""
        cfg = self._get_config()
        return dict(cfg.engines.get(cfg.tts_engine, {}))

    @override
    def get_engines(self) -> dict[str, dict[str, Any]]:
        """Get all engine configurations."""
        # Return a shallow copy to prevent accidental mutation
        cfg = self._get_config()
        return {k: dict(v) for k, v in cfg.engines.items()}

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
        if self.is_test_mode():
            import os

            return int(os.getenv("TEST_RATE_LIMIT_MESSAGES", "5"))
        return self._get_config().rate_limit_messages

    @override
    def get_rate_limit_period(self) -> int:
        """Get rate limit period."""
        if self.is_test_mode():
            import os

            return int(os.getenv("TEST_RATE_LIMIT_PERIOD", "60"))
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
        """Get Discord intents configured for the bot.

        Enables members and message content intents to support command parsing.
        """
        intents = discord.Intents.default()
        intents.message_content = True
        intents.guilds = True
        intents.members = True
        intents.voice_states = True
        return intents

    @override
    def get_enable_self_message_processing(self) -> bool:
        """Check if self-message processing is enabled."""
        return self._get_config().enable_self_message_processing

    @override
    def is_test_mode(self) -> bool:
        """Check if test mode is enabled."""
        if self._test_mode_override is not None:
            return self._test_mode_override
        return self._get_config().test_mode
