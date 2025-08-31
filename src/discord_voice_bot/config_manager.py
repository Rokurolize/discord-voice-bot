"""Configuration manager implementation that wraps the Config dataclass.

This adapter allows components that depend on the ``ConfigManager`` protocol to
operate with the newer immutable ``Config`` dataclass while avoiding circular
imports and providing convenience helpers.
"""

from copy import deepcopy
from typing import Any, cast

from .config import DEFAULT_AIVIS_URL, DEFAULT_VOICEVOX_URL, Config


class ConfigManagerImpl:
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

    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value by key."""
        config = self._get_config()
        return getattr(config, key, default)

    def get_api_url(self) -> str:
        """Get TTS API URL from current engine configuration."""
        cfg = self._get_config()
        ec = cfg.engines.get(cfg.tts_engine, {})
        # Use SSOT defaults from config for engine-specific fallback
        default_url = DEFAULT_AIVIS_URL if cfg.tts_engine == "aivis" else DEFAULT_VOICEVOX_URL
        return ec.get("url", default_url)

    def get_speaker_id(self) -> int:
        """Get default speaker ID for current engine."""
        cfg = self._get_config()
        ec = cfg.engines.get(cfg.tts_engine, {})
        # Engine-specific sensible defaults
        default_sid = {"voicevox": 3, "aivis": 1512153250}.get(cfg.tts_engine, 3)
        return int(ec.get("default_speaker", default_sid))

    def get_tts_engine(self) -> str:
        """Get TTS engine name."""
        return self._get_config().tts_engine

    def get_audio_sample_rate(self) -> int:
        """Get audio sample rate."""
        return self._get_config().audio_sample_rate

    def get_audio_channels(self) -> int:
        """Get audio channels."""
        return self._get_config().audio_channels

    def get_log_level(self) -> str:
        """Get logging level."""
        return self._get_config().log_level

    def validate(self) -> None:
        """Validate configuration (lightweight sanity checks)."""
        cfg = self._get_config()
        if not cfg.discord_token:
            raise ValueError("discord_token is empty")
        if not cfg.test_mode and getattr(cfg, "target_voice_channel_id", 0) <= 0:
            raise ValueError("target_voice_channel_id must be a positive integer in non-test mode")
        if cfg.tts_engine not in cfg.engines:
            raise ValueError(f"unknown tts_engine: {cfg.tts_engine!r}")

    # Additional convenience methods for specific config access
    def get_discord_token(self) -> str:
        """Get Discord bot token."""
        return self._get_config().discord_token

    def get_target_guild_id(self) -> int:
        """Get target guild ID."""
        return self._get_config().target_guild_id

    def get_target_voice_channel_id(self) -> int:
        """Get target voice channel ID."""
        # In test mode, use env override if provided; otherwise a fixed default
        if self.is_test_mode():
            import os

            v = os.getenv("TEST_TARGET_VOICE_CHANNEL_ID", "123456789")
            try:
                n = int(v)
                if n > 0:
                    return n
            except ValueError:
                pass
            return 123456789
        channel_id = int(self._get_config().target_voice_channel_id)
        if channel_id <= 0:
            raise ValueError("target_voice_channel_id must be a positive integer")
        return channel_id

    def get_command_prefix(self) -> str:
        """Get command prefix."""
        return self._get_config().command_prefix

    def get_engine_config(self) -> dict[str, Any]:
        """Get current TTS engine configuration."""
        cfg = self._get_config()
        # Deep copy to avoid accidental mutation of nested mappings (e.g., "speakers")
        return cast(dict[str, Any], deepcopy(cfg.engines.get(cfg.tts_engine, {})))

    def get_engines(self) -> dict[str, dict[str, Any]]:
        """Get all engine configurations."""
        # Return a shallow copy to prevent accidental mutation
        cfg = self._get_config()
        # Deep copy to avoid callers mutating nested dicts
        return {k: cast(dict[str, Any], deepcopy(v)) for k, v in cfg.engines.items()}

    def get_max_message_length(self) -> int:
        """Get maximum message length."""
        return self._get_config().max_message_length

    def get_message_queue_size(self) -> int:
        """Get message queue size."""
        return self._get_config().message_queue_size

    def get_reconnect_delay(self) -> int:
        """Get reconnect delay."""
        return self._get_config().reconnect_delay

    def get_rate_limit_messages(self) -> int:
        """Get rate limit messages."""
        if self.is_test_mode():
            return self._get_env_int("TEST_RATE_LIMIT_MESSAGES", 5)
        return self._get_config().rate_limit_messages

    def get_rate_limit_period(self) -> int:
        """Get rate limit period."""
        if self.is_test_mode():
            return self._get_env_int("TEST_RATE_LIMIT_PERIOD", 60)
        return self._get_config().rate_limit_period

    def _get_env_int(self, name: str, default: int) -> int:
        import os

        v = os.getenv(name, str(default))
        try:
            n = int(v)
            if n >= 0:
                return n
        except ValueError:
            pass
        return default

    def get_log_file(self) -> str | None:
        """Get log file path."""
        return self._get_config().log_file

    def is_debug(self) -> bool:
        """Check if debug mode is enabled."""
        return self._get_config().debug

    def get_intents(self) -> Any:
        """Get Discord intents configured for the bot."""
        # Delegate to Config to keep a single source of truth
        return self._get_config().get_intents()

    def get_enable_self_message_processing(self) -> bool:
        """Check if self-message processing is enabled."""
        return self._get_config().enable_self_message_processing

    def is_test_mode(self) -> bool:
        """Check if test mode is enabled."""
        if self._test_mode_override is not None:
            return self._test_mode_override
        return self._get_config().test_mode
