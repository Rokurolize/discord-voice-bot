"""Configuration manager implementation that wraps the Config dataclass.

This adapter allows components that depend on the ``ConfigManager`` protocol to
operate with the newer immutable ``Config`` dataclass while avoiding circular
imports and providing convenience helpers.
"""

from collections.abc import Mapping
from copy import deepcopy
from typing import Any, cast
from urllib.parse import urlparse

from loguru import logger

from .config import (
    AIVIS_SPEAKERS_DEFAULT,
    DEFAULT_AIVIS_URL,
    DEFAULT_VOICEVOX_URL,
    VOICEVOX_SPEAKERS_DEFAULT,
    Config,
)

# Test-only environment variable names (centralized for discoverability)
TEST_RATE_LIMIT_MESSAGES_ENV = "TEST_RATE_LIMIT_MESSAGES"
TEST_RATE_LIMIT_PERIOD_ENV = "TEST_RATE_LIMIT_PERIOD"
TEST_TARGET_VOICE_CHANNEL_ID_ENV = "TEST_TARGET_VOICE_CHANNEL_ID"
TEST_TARGET_VOICE_CHANNEL_ID_DEFAULT = 123456789
DEFAULT_SPEAKER_IDS: dict[str, int] = {"voicevox": 3, "aivis": 1512153250}


class ConfigManagerImpl:
    """Configuration manager that adapts a ``Config`` dataclass to the protocol."""

    def _normalize_to_plain_dict(self, m: Mapping[str, Any]) -> dict[str, Any]:
        """
        Normalize a nested Mapping into a plain dict with string keys.

        Args:
            m: Mapping to normalize.

        Returns:
            dict[str, Any]: A new plain dict with string keys and normalized, deep-copied contents.

        """

        def _norm(x: Any) -> Any:
            if isinstance(x, Mapping):
                mm = cast(Mapping[Any, Any], x)
                return {cast(str, k): _norm(v) for k, v in mm.items()}
            if isinstance(x, list):
                ll = cast(list[Any], x)
                return [_norm(i) for i in ll]
            if isinstance(x, tuple):
                tt = cast(tuple[Any, ...], x)
                return [_norm(i) for i in tt]
            return deepcopy(x)

        mm = cast(Mapping[Any, Any], m)
        return {cast(str, k): _norm(v) for k, v in mm.items()}

    def __init__(self, config: Config | None = None, *, test_mode: bool | None = None) -> None:
        """
        Initialize the configuration manager.

        If `config` is provided it will be used directly; otherwise the manager lazily loads a Config from the environment on first access. If `test_mode` is not None it overrides the config's test mode value returned by is_test_mode().

        Args:
            config: Optional Config dataclass to use instead of loading from environment.
            test_mode: Optional boolean that, when set, overrides the configured test mode.

        """
        super().__init__()
        self._config: Config | None = config
        self._test_mode_override = test_mode

    def _validate_custom_engine(self, name: str, ec: Mapping[str, Any]) -> None:
        """
        Validate that a non-built-in TTS engine configuration contains required fields.

        If `name` is a built-in engine ("voicevox" or "aivis") no validation is performed.
        For other engine names, ensures `ec` contains a truthy "url" and the key "default_speaker".

        Args:
            name: The engine name being validated.
            ec: Mapping containing the engine configuration.

        Raises:
            ValueError: If a custom engine is missing a required "url" or "default_speaker".

        """
        if name in ("voicevox", "aivis"):
            return
        if not ec.get("url"):
            raise ValueError("custom engine requires 'url' in engines[engine]")
        if "default_speaker" not in ec:
            raise ValueError("custom engine requires 'default_speaker' in engines[engine]")

    def _get_config(self) -> Config:
        """Get configuration instance, creating it if necessary."""
        if self._config is None:
            self._config = Config.from_env()
        return self._config

    def config(self) -> Config:
        """
        Return the effective Config dataclass used by this manager.

        This accessor exposes the underlying Config instance (lazily loaded from environment if the
        manager was constructed without an explicit Config). The returned Config is the canonical,
        immutable configuration object used by the manager — callers should treat it as read-only.

        Returns:
            Config: The active configuration dataclass.

        """
        return self._get_config()

    def get(self, key: str, default: Any = None) -> Any:
        """
        Return the value of a named attribute from the underlying Config.

        Looks up attribute `key` on the adapter's Config and returns it; if the attribute
        does not exist, returns `default`.
        """
        config = self._get_config()
        return getattr(config, key, default)

    def get_api_url(self) -> str:
        """
        Return the resolved TTS API URL for the current engine.

        Returns:
            str: Resolved TTS API URL.

        Raises:
            ValueError: If the configured `tts_engine` is not recognized, or if a custom (non-built-in) engine provides an invalid or missing `url`, or if no default is available.

        """
        cfg = self._get_config()
        # Consistency: require declared engine unless using known defaults
        if cfg.tts_engine not in cfg.engines and cfg.tts_engine not in ("aivis", "voicevox"):
            raise ValueError(f"unknown tts_engine: {cfg.tts_engine!r}")
        # Prefer explicit URL when provided in engine config
        ec = cfg.engines.get(cfg.tts_engine)
        if ec is not None and "url" in ec:
            url = str(ec["url"]).strip()
            pu = urlparse(url)
            if url and pu.scheme in ("http", "https") and pu.netloc:
                return url
            if cfg.tts_engine in ("aivis", "voicevox"):
                logger.warning(f"Invalid URL for built-in engine {cfg.tts_engine!r}: {ec['url']!r}. Falling back to default.")
            else:
                raise ValueError(f"invalid url for engine {cfg.tts_engine!r}: {ec['url']!r}")
        # Known-engine defaults
        if cfg.tts_engine == "aivis":
            return DEFAULT_AIVIS_URL
        if cfg.tts_engine == "voicevox":
            return DEFAULT_VOICEVOX_URL
        # Unknown engine without URL/default
        raise ValueError(f"unknown or unsupported tts_engine {cfg.tts_engine!r}; provide an explicit 'url' under engines[engine] or switch to a supported engine")

    def get_speaker_id(self) -> int:
        """
        Return the default speaker ID for the currently configured TTS engine.

        If the configured engine has no explicit entry in config.engines, a baked-in default from DEFAULT_SPEAKER_IDS is returned when available. For a configured engine mapping, the engine is validated (must provide required fields for custom engines), then the mapping's "default_speaker" value is used; if absent, the baked-in default is used when present. The value is coerced to int and must be a positive integer.

        Returns:
            int: The default speaker ID.

        Raises:
            ValueError: If the tts_engine is unknown, if the configured `default_speaker` cannot be converted to an integer, or if the resulting ID is not a positive integer.

        """
        cfg = self._get_config()
        ec = cfg.engines.get(cfg.tts_engine)
        # Allow built-in engines without explicit mapping (fallback to baked-in defaults)
        if ec is None:
            default_sid = DEFAULT_SPEAKER_IDS.get(cfg.tts_engine)
            if default_sid is not None:
                return default_sid
            raise ValueError(f"unknown tts_engine: {cfg.tts_engine!r}")
        # Custom engine sanity (no baked-in defaults)
        self._validate_custom_engine(cfg.tts_engine, ec)
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
        """Return the configured audio sample rate in Hz."""
        return self._get_config().audio_sample_rate

    def get_audio_channels(self) -> int:
        """Return the configured number of audio channels."""
        return self._get_config().audio_channels

    def get_log_level(self) -> str:
        """Return the configured log level name (e.g., "INFO")."""
        return self._get_config().log_level

    def validate(self) -> None:
        """
        Perform lightweight sanity checks of the loaded configuration.

        Checks performed (raises ValueError on failure):
        - discord_token must be non-empty.
        - tts_engine must be either a known built-in ("aivis", "voicevox") or present in cfg.engines.
        - For custom engines (present in cfg.engines), ensures required fields via _validate_custom_engine.
        - In non-test mode:
          - target_voice_channel_id and target_guild_id must be positive integers.
          - audio_sample_rate must be > 0.
          - audio_channels must be 1 or 2.
          - audio_frame_duration must be a positive divisor of 1000.
          - rate_limit_messages and rate_limit_period must be > 0.
          - reconnect_delay and message_queue_size must be >= 0.
          - max_message_length must be > 0.
        - Performs a lightweight API URL validation via get_api_url(); for built-in engines with an explicitly configured invalid URL, logs a warning and falls back to the built-in default; otherwise an invalid URL raises ValueError.

        This method does not modify configuration; it only raises ValueError for the concrete invalid conditions listed above.
        """
        cfg = self._get_config()
        if not cfg.discord_token:
            raise ValueError("discord_token is empty")
        if not cfg.test_mode and getattr(cfg, "target_voice_channel_id", 0) <= 0:
            raise ValueError("target_voice_channel_id must be a positive integer in non-test mode")
        if cfg.tts_engine not in cfg.engines and cfg.tts_engine not in ("aivis", "voicevox"):
            raise ValueError(f"unknown tts_engine: {cfg.tts_engine!r}")
        # Custom engine sanity (no baked-in defaults)
        if cfg.tts_engine in cfg.engines:
            self._validate_custom_engine(cfg.tts_engine, cfg.engines[cfg.tts_engine])
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
        # Validate URL shape early (lightweight parse). For built-ins with invalid explicit URL, warn and fall back.
        try:
            _ = self.get_api_url()
        except ValueError as e:
            cfg = self._get_config()
            if cfg.tts_engine in ("aivis", "voicevox") and cfg.tts_engine in cfg.engines and cfg.engines[cfg.tts_engine].get("url"):
                logger.warning(f"Invalid URL configured for built-in engine {cfg.tts_engine!r}: {e}. Falling back to default.")
            else:
                raise

    # Additional convenience methods for specific config access
    def get_discord_token(self) -> str:
        """
        Return the Discord bot token from the loaded configuration.

        Returns:
            str: The configured Discord bot token.

        """
        return self._get_config().discord_token

    def get_target_guild_id(self) -> int:
        """
        Return the configured target Discord guild (server) ID.

        Returns:
            int: The target guild ID from the loaded configuration.

        """
        return self._get_config().target_guild_id

    def get_target_voice_channel_id(self) -> int:
        """
        Return the configured Discord target voice channel ID.

        If test mode is active, reads TEST_TARGET_VOICE_CHANNEL_ID from the environment (falls back to the module default)
        and returns that value (must be >= 1). Otherwise returns the configured `target_voice_channel_id` from the
        loaded Config after converting to int.

        Returns:
            int: A positive voice channel ID.

        Raises:
            ValueError: If the resolved channel ID is not a positive integer.

        """
        # In test mode, use TEST_TARGET_VOICE_CHANNEL_ID if set; otherwise default (env-first for test determinism)
        if self.is_test_mode():
            return self._get_env_int(TEST_TARGET_VOICE_CHANNEL_ID_ENV, TEST_TARGET_VOICE_CHANNEL_ID_DEFAULT, min_value=1)
        channel_id = int(self._get_config().target_voice_channel_id)
        if channel_id <= 0:
            raise ValueError("target_voice_channel_id must be a positive integer")
        return channel_id

    def get_command_prefix(self) -> str:
        """
        Return the configured command prefix used to invoke bot commands.

        Returns:
            str: The command prefix from the active configuration.

        """
        return self._get_config().command_prefix

    def get_engine_config(self) -> dict[str, Any]:
        """
        Return a plain dict describing the configuration for the currently selected TTS engine.

        If the configured engine has an explicit entry in the `engines` mapping, that mapping is validated for required fields (custom engines must provide a `url` and `default_speaker`) and returned as a normalized plain dict (nested mappings/lists converted to standard Python dicts/lists/tuples).

        If the configured engine has no explicit mapping and is one of the built-in engines (`"aivis"` or `"voicevox"`), a dictionary with sensible defaults is returned:
        - "url": the built-in default URL for the engine,
        - "default_speaker": the engine's baked-in default speaker id,
        - "speakers": a copy of the engine's default speakers mapping.

        Returns:
            dict[str, Any]: Normalized engine configuration.

        Raises:
            ValueError: If the configured TTS engine is unknown or a custom engine is missing required fields.

        """
        cfg = self._get_config()
        ec = cfg.engines.get(cfg.tts_engine)
        if ec is None:
            if cfg.tts_engine == "aivis":
                return {
                    "url": DEFAULT_AIVIS_URL,
                    "default_speaker": DEFAULT_SPEAKER_IDS["aivis"],
                    "speakers": AIVIS_SPEAKERS_DEFAULT.copy(),
                }
            if cfg.tts_engine == "voicevox":
                return {
                    "url": DEFAULT_VOICEVOX_URL,
                    "default_speaker": DEFAULT_SPEAKER_IDS["voicevox"],
                    "speakers": VOICEVOX_SPEAKERS_DEFAULT.copy(),
                }
            raise ValueError(f"unknown tts_engine: {cfg.tts_engine!r}")
        # Custom engine sanity (no baked-in defaults)
        self._validate_custom_engine(cfg.tts_engine, ec)
        return self._normalize_to_plain_dict(cast(Mapping[str, Any], ec))

    def get_engines(self) -> dict[str, dict[str, Any]]:
        """
        Return a mapping of engine name -> engine configuration as plain Python dicts.

        Each value is a normalized dict representation of the engine's configuration (nested Mapping, list, and tuple structures are converted to plain dicts/lists/tuples and deep-copied), suitable for external use and safe to mutate.
        """
        # Return plain dicts; convert nested mappings to dicts to avoid leaking MappingProxyType
        cfg = self._get_config()
        return {name: self._normalize_to_plain_dict(cast(Mapping[str, Any], ev)) for name, ev in cfg.engines.items()}

    def get_max_message_length(self) -> int:
        """
        Return the configured maximum message length.

        Returns:
            int: Maximum allowed message length from the underlying Config.

        """
        return self._get_config().max_message_length

    def get_message_queue_size(self) -> int:
        """
        Return the configured maximum message queue size.

        This reads the value from the underlying Config and represents the maximum number
        of pending messages allowed in the bot's message queue.
        """
        return self._get_config().message_queue_size

    def get_reconnect_delay(self) -> int:
        """
        Return the configured reconnect delay in seconds.

        Returns:
            int: Reconnect delay (seconds) as specified in the active Config.

        """
        return self._get_config().reconnect_delay

    def get_rate_limit_messages(self) -> int:
        """
        Return the configured number of allowed messages in the rate window.

        In test mode, this value is read from the TEST_RATE_LIMIT_MESSAGES_ENV environment variable (defaults to 5 and must be at least 1). Otherwise returns the Config.rate_limit_messages value.
        """
        if self.is_test_mode():
            return self._get_env_int(TEST_RATE_LIMIT_MESSAGES_ENV, 5, min_value=1)
        return self._get_config().rate_limit_messages

    def get_rate_limit_period(self) -> int:
        """
        Return the configured rate limit period in seconds.

        In normal operation this returns the value from the loaded Config. When test mode is active, the value is read from the environment variable TEST_RATE_LIMIT_PERIOD_ENV (parsed as an integer, minimum 1) with a default of 60 seconds.

        Returns:
            int: Rate limit period in seconds.

        """
        if self.is_test_mode():
            return self._get_env_int(TEST_RATE_LIMIT_PERIOD_ENV, 60, min_value=1)
        return self._get_config().rate_limit_period

    def _get_env_int(self, name: str, default: int, *, min_value: int = 0) -> int:
        """
        Read an integer from an environment variable with normalization and bounds-checking.

        Strips underscores, spaces, and commas from the environment value, attempts to parse it as an int,
        and returns the parsed value if it is >= min_value. If the environment variable is unset,
        non-numeric after normalization, or below min_value, returns the provided default.

        Args:
            name: Environment variable name to read.
            default: Value to return if the environment variable is missing, invalid, or below min_value.
            min_value: Minimum allowed value (inclusive). Defaults to 0.

        Returns:
            int: The parsed environment integer or the default.

        """
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
        """
        Return the configured log file path, or None if no file is configured.

        Returns:
            str | None: Path to the log file, or None when logging to stderr/stdout.

        """
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
