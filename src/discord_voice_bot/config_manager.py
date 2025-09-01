"""Configuration manager implementation that wraps the Config dataclass.

This adapter allows components that depend on the ``ConfigManager`` protocol to
operate with the newer immutable ``Config`` dataclass while avoiding circular
imports and providing convenience helpers.
"""

from collections.abc import Mapping
from copy import deepcopy
from typing import Any, cast

from .config import DEFAULT_AIVIS_URL, DEFAULT_VOICEVOX_URL, Config

# Test-only environment variable names (centralized for discoverability)
TEST_RATE_LIMIT_MESSAGES_ENV = "TEST_RATE_LIMIT_MESSAGES"
TEST_RATE_LIMIT_PERIOD_ENV = "TEST_RATE_LIMIT_PERIOD"
TEST_TARGET_VOICE_CHANNEL_ID_ENV = "TEST_TARGET_VOICE_CHANNEL_ID"
TEST_TARGET_VOICE_CHANNEL_ID_DEFAULT = 123456789
DEFAULT_SPEAKER_IDS: dict[str, int] = {"voicevox": 3, "aivis": 1512153250}


class ConfigManagerImpl:
    """Configuration manager that adapts a ``Config`` dataclass to the protocol."""

    def _normalize_to_plain_dict(self, m: Mapping[str, Any]) -> dict[str, Any]:
        def _norm(x: Any) -> Any:
            if isinstance(x, Mapping):
                mm = cast(Mapping[Any, Any], x)
                return {cast(str, k): _norm(v) for k, v in mm.items()}
            if isinstance(x, list):
                ll = cast(list[Any], x)
                return [_norm(i) for i in ll]
            if isinstance(x, tuple):
                tt = cast(tuple[Any, ...], x)
                return tuple(_norm(i) for i in tt)
            return deepcopy(x)

        mm = cast(Mapping[Any, Any], m)
        return {cast(str, k): _norm(v) for k, v in mm.items()}

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

    def config(self) -> Config:
        """Public accessor for the underlying Config (avoids private usage)."""
        return self._get_config()

    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value by key."""
        config = self._get_config()
        return getattr(config, key, default)

    def get_api_url(self) -> str:
        """Get TTS API URL from current engine configuration."""
        cfg = self._get_config()
        # Consistency: require declared engine unless using known defaults
        if cfg.tts_engine not in cfg.engines and cfg.tts_engine not in ("aivis", "voicevox"):
            raise ValueError(f"unknown tts_engine: {cfg.tts_engine!r}")
        # Prefer explicit URL when provided in engine config
        ec = cfg.engines.get(cfg.tts_engine)
        if ec is not None and "url" in ec:
            url = str(ec["url"]).strip()  # minimal validation for common mistakes
            if not url:
                raise ValueError(f"invalid url for engine {cfg.tts_engine!r}: {ec['url']!r} (empty)")
            try:
                from urllib.parse import urlparse

                pu = urlparse(url)
                if pu.scheme in ("http", "https") and pu.netloc:
                    return url
            except Exception:
                pass
            raise ValueError(f"invalid url for engine {cfg.tts_engine!r}: {url!r}")
        # Known-engine defaults
        if cfg.tts_engine == "aivis":
            return DEFAULT_AIVIS_URL
        if cfg.tts_engine == "voicevox":
            return DEFAULT_VOICEVOX_URL
        # Unknown engine without URL/default
        raise ValueError(f"unknown or unsupported tts_engine {cfg.tts_engine!r}; provide an explicit 'url' under engines[engine] or switch to a supported engine")

    def get_speaker_id(self) -> int:
        """Get default speaker ID for current engine."""
        cfg = self._get_config()
        ec = cfg.engines.get(cfg.tts_engine)
        # Allow built-in engines without explicit mapping (fallback to baked-in defaults)
        if ec is None:
            default_sid = DEFAULT_SPEAKER_IDS.get(cfg.tts_engine)
            if default_sid is not None:
                return default_sid
            raise ValueError(f"unknown tts_engine: {cfg.tts_engine!r}")
        # Custom engine sanity (no baked-in defaults)
        if cfg.tts_engine not in ("aivis", "voicevox"):
            if not ec.get("url"):
                raise ValueError("custom engine requires 'url' in engines[engine]")
            if "default_speaker" not in ec:
                raise ValueError("custom engine requires 'default_speaker' in engines[engine]")
        default_sid = DEFAULT_SPEAKER_IDS.get(cfg.tts_engine)
        raw_sid = ec.get("default_speaker", default_sid)
        try:
            sid = int(raw_sid)
        except (TypeError, ValueError):
            raise ValueError("default_speaker must be an integer") from None
        if sid <= 0:
            raise ValueError("default_speaker must be a positive integer")
        return sid

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
            if cfg.tts_engine not in ("aivis", "voicevox"):
                raise ValueError(f"unknown tts_engine: {cfg.tts_engine!r}")
        # Custom engine sanity (no baked-in defaults)
        if cfg.tts_engine not in ("aivis", "voicevox"):
            ec = cfg.engines[cfg.tts_engine]
            if not ec.get("url"):
                raise ValueError("custom engine requires 'url' in engines[engine]")
            if "default_speaker" not in ec:
                raise ValueError("custom engine requires 'default_speaker' in engines[engine]")
        if not cfg.test_mode and getattr(cfg, "target_guild_id", 0) <= 0:
            raise ValueError("target_guild_id must be a positive integer in non-test mode")
        if not cfg.test_mode and getattr(cfg, "audio_sample_rate", 0) <= 0:
            raise ValueError("audio_sample_rate must be > 0 in non-test mode")
        if not cfg.test_mode and getattr(cfg, "audio_channels", 0) not in (1, 2):
            raise ValueError("audio_channels must be 1 or 2 in non-test mode")
        # Optional: typical audio constraints & rate limits
        if not cfg.test_mode:
            afd = getattr(cfg, "audio_frame_duration", 0)
            if afd <= 0 or (1000 % afd) != 0:
                raise ValueError("audio_frame_duration must be a positive divisor of 1000 (e.g., 20)")
            if getattr(cfg, "rate_limit_messages", 0) <= 0:
                raise ValueError("rate_limit_messages must be > 0 in non-test mode")
            if getattr(cfg, "rate_limit_period", 0) <= 0:
                raise ValueError("rate_limit_period must be > 0 in non-test mode")
        # Additional non-test constraints
        if not cfg.test_mode and getattr(cfg, "reconnect_delay", 0) < 0:
            raise ValueError("reconnect_delay must be >= 0 in non-test mode")
        if not cfg.test_mode and getattr(cfg, "message_queue_size", 0) < 0:
            raise ValueError("message_queue_size must be >= 0 in non-test mode")
        if not cfg.test_mode and getattr(cfg, "max_message_length", 0) <= 0:
            raise ValueError("max_message_length must be > 0 in non-test mode")

    # Additional convenience methods for specific config access
    def get_discord_token(self) -> str:
        """Get Discord bot token."""
        return self._get_config().discord_token

    def get_target_guild_id(self) -> int:
        """Get target guild ID."""
        return self._get_config().target_guild_id

    def get_target_voice_channel_id(self) -> int:
        """Get target voice channel ID."""
        # In test mode, use TEST_TARGET_VOICE_CHANNEL_ID if set; otherwise default (env-first for test determinism)
        if self.is_test_mode():
            return self._get_env_int(TEST_TARGET_VOICE_CHANNEL_ID_ENV, TEST_TARGET_VOICE_CHANNEL_ID_DEFAULT, min_value=1)
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
        ec = cfg.engines.get(cfg.tts_engine)
        if ec is None:
            if cfg.tts_engine == "aivis":
                return {"url": DEFAULT_AIVIS_URL, "default_speaker": DEFAULT_SPEAKER_IDS["aivis"]}
            if cfg.tts_engine == "voicevox":
                return {"url": DEFAULT_VOICEVOX_URL, "default_speaker": DEFAULT_SPEAKER_IDS["voicevox"]}
            raise ValueError(f"unknown tts_engine: {cfg.tts_engine!r}")
        # Custom engine sanity (no baked-in defaults)
        if cfg.tts_engine not in ("aivis", "voicevox"):
            if not ec.get("url"):
                raise ValueError("custom engine requires 'url' in engines[engine]")
            if "default_speaker" not in ec:
                raise ValueError("custom engine requires 'default_speaker' in engines[engine]")
        return self._normalize_to_plain_dict(cast(Mapping[str, Any], ec))

    def get_engines(self) -> dict[str, dict[str, Any]]:
        """Get all engine configurations."""
        # Return plain dicts; convert nested mappings to dicts to avoid leaking MappingProxyType
        cfg = self._get_config()
        return {name: self._normalize_to_plain_dict(cast(Mapping[str, Any], ev)) for name, ev in cfg.engines.items()}

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
            return self._get_env_int(TEST_RATE_LIMIT_MESSAGES_ENV, 5, min_value=1)
        return self._get_config().rate_limit_messages

    def get_rate_limit_period(self) -> int:
        """Get rate limit period."""
        if self.is_test_mode():
            return self._get_env_int(TEST_RATE_LIMIT_PERIOD_ENV, 60, min_value=1)
        return self._get_config().rate_limit_period

    def _get_env_int(self, name: str, default: int, *, min_value: int = 0) -> int:
        import os

        v = os.getenv(name)
        if v is None:
            return default
        v = v.strip().replace("_", "").replace(" ", "").replace(",", "")
        try:
            n = int(v)
            if n >= min_value:
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
