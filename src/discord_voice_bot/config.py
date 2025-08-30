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

import discord
from dotenv import load_dotenv

# Shared defaults (SSOT) for engine URLs
DEFAULT_VOICEVOX_URL = "http://localhost:50021"
DEFAULT_AIVIS_URL = "http://127.0.0.1:10101"


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
        """Load configuration from environment variables."""
        # 1. Load secrets file first (production)
        secrets_path = os.environ.get("SECRETS_FILE", "~/.config/discord-voice-bot/secrets.env")
        secrets_file = Path(secrets_path).expanduser()
        if secrets_file.exists():
            _ = load_dotenv(secrets_file)

        # 2. Load local .env file (development/testing) - this overrides secrets
        local_env = Path(".env")
        if local_env.exists():
            # Respect existing process environment for secrets like tokens,
            # but allow .env to override defaults from secrets.env.
            prev_token = os.environ.get("DISCORD_BOT_TOKEN")
            _ = load_dotenv(local_env, override=True)
            if prev_token is not None:
                os.environ["DISCORD_BOT_TOKEN"] = prev_token

        # Build typed engine configurations
        voicevox_cfg: EngineConfig = {
            "url": os.environ.get("VOICEVOX_URL", DEFAULT_VOICEVOX_URL),
            "default_speaker": 3,
            "speakers": MappingProxyType(
                {
                    "normal": 3,
                    "sexy": 5,
                    "tsun": 7,
                    "amai": 1,
                }
            ),
        }
        voicevox_ro: EngineConfig = cast(EngineConfig, MappingProxyType(voicevox_cfg))

        aivis_cfg: EngineConfig = {
            "url": os.environ.get("AIVIS_URL", DEFAULT_AIVIS_URL),
            "default_speaker": 1512153250,
            "speakers": MappingProxyType(
                {
                    "anneli_normal": 888753760,
                    "mai": 1431611904,
                    "chuunibyou": 604166016,
                    "zunda_normal": 1512153250,
                }
            ),
        }
        aivis_ro: EngineConfig = cast(EngineConfig, MappingProxyType(aivis_cfg))

        engines_map: dict[str, EngineConfig] = {
            "voicevox": voicevox_ro,
            "aivis": aivis_ro,
        }

        return cls(
            discord_token=os.environ.get("DISCORD_BOT_TOKEN", ""),
            target_guild_id=_env_to_int("TARGET_GUILD_ID", 0),
            target_voice_channel_id=_env_to_int("TARGET_VOICE_CHANNEL_ID", 0),
            tts_engine=os.environ.get("TTS_ENGINE", "voicevox").lower(),
            tts_speaker=os.environ.get("TTS_SPEAKER", "normal").lower(),
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
            debug=os.environ.get("DEBUG", "false").lower() in ["true", "1", "yes"],
            test_mode=os.environ.get("TEST_MODE", "false").lower() in ["true", "1", "yes"],
            enable_self_message_processing=os.environ.get("ENABLE_SELF_MESSAGE_PROCESSING", "false").lower() in ["true", "1", "yes"],
        )

    # Backward-compat helper for tests that expect this on Config
    def get_intents(self) -> Any:
        """Return Discord intents suitable for this bot.

        Enables message content, guilds, members, and voice state intents.
        """
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
