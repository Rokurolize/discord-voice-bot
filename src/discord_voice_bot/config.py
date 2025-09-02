"""Configuration management for Discord Voice TTS Bot.

Module-level defaults are defined here to act as a single source of truth
for engine URLs and other shared constants. Import these values elsewhere
instead of re-declaring literals to avoid drift.
"""

import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any, TypedDict, cast

from dotenv import dotenv_values

# Shared defaults (SSOT) for engine URLs
DEFAULT_VOICEVOX_URL = "http://localhost:50021"
DEFAULT_AIVIS_URL = "http://127.0.0.1:10101"

# Shared speaker maps (SSOT)
VOICEVOX_SPEAKERS_DEFAULT: dict[str, int] = {"normal": 3, "sexy": 5, "tsun": 7, "amai": 1}
AIVIS_SPEAKERS_DEFAULT: dict[str, int] = {
    "anneli_normal": 888753760,
    "mai": 1431611904,
    "chuunibyou": 604166016,
    "zunda_normal": 1512153250,
}


def _env_to_int(key: str, default: int) -> int:
    """Safely convert an environment variable to an integer.

    - Trims surrounding whitespace
    - Allows underscores in numbers (e.g., "1_000")
    - Returns ``default`` on any parsing failure
    """
    val_raw = os.environ.get(key)
    if val_raw is None:
        return default
    val = val_raw.strip().replace("_", "")
    try:
        return int(val, 10)
    except ValueError:
        return default


def _env_to_nonneg_int(key: str, default: int) -> int:
    """Return environment variable as non-negative int.

    Falls back to ``default`` if parsing fails or the parsed value is negative.
    """
    val = _env_to_int(key, default)
    return default if val < 0 else val


def _env_to_bool(key: str, default: bool) -> bool:
    """
    Return the boolean value of an environment variable.

    If the environment variable named by `key` is not set, returns `default`. When present,
    the value is trimmed and compared case-insensitively to common truthy tokens: `"true"`, `"1"`, `"yes"`, and `"on"`. Any other value yields False.

    Args:
        key: Name of the environment variable to read.
        default: Value to return when the environment variable is not set.

    Returns:
        bool: Parsed boolean value or `default` if the variable is missing.

    """
    val = os.environ.get(key)
    if val is None:
        return default
    return val.strip().lower() in ("true", "1", "yes", "on")


class EngineConfig(TypedDict):
    url: str
    default_speaker: int
    speakers: Mapping[str, int]


@dataclass(frozen=True, kw_only=True)
class Config:
    """Configuration for the Discord Voice TTS Bot."""

    discord_token: str
    target_guild_id: int
    target_voice_channel_id: int
    tts_engine: str
    tts_speaker: str
    engines: Mapping[str, EngineConfig]
    command_prefix: str
    max_message_length: int
    message_queue_size: int
    reconnect_delay: int
    audio_sample_rate: int
    audio_channels: int
    audio_frame_duration: int
    rate_limit_messages: int
    rate_limit_period: int
    log_level: str
    log_file: str | None
    debug: bool
    test_mode: bool
    enable_self_message_processing: bool

    @classmethod
    def from_env(cls) -> "Config":
        """
        Create a Config instance by loading settings from the environment, secrets file, and a local .env with the following precedence: process environment > .env > secrets > built-in defaults.

        Detailed behavior:
        - Seeds missing environment variables from a secrets file (path from SECRETS_FILE or default) and a local .env; local .env values override secrets.
        - Constructs typed, immutable engine configurations for "voicevox" and "aivis" (each an EngineConfig) and exposes them in a read-only mapping on the resulting Config.
        - If TTS_SPEAKER is set and matches a known speaker label for the selected TTS_ENGINE (TTS_ENGINE, case-insensitive), the matching numeric speaker ID is applied as that engine's default_speaker.
        - Normalizes several numeric and boolean settings using helper converters; provides sensible defaults when values are missing or invalid.
        - Detects test mode either from TEST_MODE or from the presence of PYTEST_CURRENT_TEST in the process environment.

        Returns:
            Config: An immutable configuration populated from environment, secrets, .env, and defaults.

        """
        # Precedence: process env > .env > secrets > defaults
        # Load secrets and .env as dicts, then seed missing keys into process env
        secrets_path = os.environ.get("SECRETS_FILE", "~/.config/discord-voice-bot/secrets.env")
        secrets_file = Path(secrets_path).expanduser()
        secrets_raw = dotenv_values(secrets_file) if secrets_file.exists() else {}
        secrets: dict[str, str] = {k: v for k, v in secrets_raw.items() if v is not None}

        local_env = Path(".env")
        local_raw = dotenv_values(local_env) if local_env.exists() else {}
        local: dict[str, str] = {k: v for k, v in local_raw.items() if v is not None}

        merged = secrets.copy()
        merged.update(local)  # .env overrides secrets
        for k, v in merged.items():
            _ = os.environ.setdefault(k, v)

        # Build typed engine configurations
        voicevox_cfg: EngineConfig = {
            "url": os.environ.get("VOICEVOX_URL", DEFAULT_VOICEVOX_URL),
            "default_speaker": 3,
            "speakers": MappingProxyType(dict(VOICEVOX_SPEAKERS_DEFAULT)),
        }
        aivis_cfg: EngineConfig = {
            "url": os.environ.get("AIVIS_URL", DEFAULT_AIVIS_URL),
            "default_speaker": 1512153250,
            "speakers": MappingProxyType(dict(AIVIS_SPEAKERS_DEFAULT)),
        }

        # -- Apply TTS_SPEAKER label -> numeric ID and reflect into default_speaker --
        engine_name = os.environ.get("TTS_ENGINE", "voicevox").lower()
        speaker_label = os.environ.get("TTS_SPEAKER", "normal").lower()
        if engine_name == "voicevox":
            sid = voicevox_cfg["speakers"].get(speaker_label)
            if sid is not None:
                voicevox_cfg["default_speaker"] = sid
        elif engine_name == "aivis":
            sid = aivis_cfg["speakers"].get(speaker_label)
            if sid is not None:
                aivis_cfg["default_speaker"] = sid

        voicevox_ro: EngineConfig = cast(EngineConfig, MappingProxyType(voicevox_cfg))
        aivis_ro: EngineConfig = cast(EngineConfig, MappingProxyType(aivis_cfg))

        engines_map: dict[str, EngineConfig] = {
            "voicevox": voicevox_ro,
            "aivis": aivis_ro,
        }

        return cls(
            discord_token=os.environ.get("DISCORD_BOT_TOKEN", ""),
            target_guild_id=_env_to_int("TARGET_GUILD_ID", 0),
            target_voice_channel_id=_env_to_int("TARGET_VOICE_CHANNEL_ID", 0),
            tts_engine=engine_name,
            tts_speaker=speaker_label,
            engines=MappingProxyType(engines_map),
            command_prefix=os.environ.get("COMMAND_PREFIX", "!tts"),
            max_message_length=_env_to_int("MAX_MESSAGE_LENGTH", 10000),
            message_queue_size=_env_to_nonneg_int("MESSAGE_QUEUE_SIZE", 10),
            reconnect_delay=_env_to_nonneg_int("RECONNECT_DELAY", 5),
            audio_sample_rate=48000,
            audio_channels=2,
            audio_frame_duration=20,
            rate_limit_messages=_env_to_nonneg_int("RATE_LIMIT_MESSAGES", 100),
            rate_limit_period=_env_to_nonneg_int("RATE_LIMIT_PERIOD", 60),
            log_level=os.environ.get("LOG_LEVEL", "DEBUG").upper(),
            log_file=os.environ.get("LOG_FILE", "discord_bot_error.log") or None,
            debug=_env_to_bool("DEBUG", False),
            # Treat pytest runs as test mode unless explicitly disabled
            test_mode=_env_to_bool("TEST_MODE", False) or ("PYTEST_CURRENT_TEST" in os.environ),
            enable_self_message_processing=_env_to_bool("ENABLE_SELF_MESSAGE_PROCESSING", False),
        )

    # Backward-compat helper for tests that expect this on Config
    def get_intents(self) -> Any:
        """
        Return a discord.Intents object configured for this bot.

        Enables message_content, guilds, members, and voice_states intents required by the bot.

        Returns:
            discord.Intents: Intents instance with the required flags enabled.

        """
        import discord

        intents = discord.Intents.default()
        intents.message_content = True
        intents.guilds = True
        intents.members = True
        intents.voice_states = True
        return intents


def get_config() -> Config:
    """Backward-compatible accessor returning configuration from environment.

    Older tests and modules expect a ``get_config`` function. This thin wrapper
    preserves that API by delegating to ``Config.from_env()``.
    """
    return Config.from_env()
