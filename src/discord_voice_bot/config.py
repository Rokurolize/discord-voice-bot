"""Configuration management for Discord Voice TTS Bot."""

import os
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping

from dotenv import load_dotenv


def _env_to_int(key: str, default: int) -> int:
    """Safely convert an environment variable to an integer."""
    val = os.environ.get(key)
    if val is None or not val.isdigit():
        return default
    return int(val)


@dataclass(frozen=True, kw_only=True)
class Config:
    """Configuration for the Discord Voice TTS Bot."""

    discord_token: str
    target_guild_id: int
    target_voice_channel_id: int
    tts_engine: str
    tts_speaker: str
    engines: Mapping[str, Mapping[str, Any]]
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
            load_dotenv(secrets_file)

        # 2. Load local .env file (development/testing) - this overrides secrets
        local_env = Path(".env")
        if local_env.exists():
            load_dotenv(local_env, override=True)

        return cls(
            discord_token=os.environ.get("DISCORD_BOT_TOKEN", ""),
            target_guild_id=_env_to_int("TARGET_GUILD_ID", 0),
            target_voice_channel_id=_env_to_int("TARGET_VOICE_CHANNEL_ID", 0),
            tts_engine=os.environ.get("TTS_ENGINE", "voicevox").lower(),
            tts_speaker=os.environ.get("TTS_SPEAKER", "normal").lower(),
            engines=MappingProxyType({
                "voicevox": MappingProxyType({
                    "url": os.environ.get("VOICEVOX_URL", "http://localhost:50021"),
                    "default_speaker": 3,
                    "speakers": MappingProxyType({
                        "normal": 3,
                        "sexy": 5,
                        "tsun": 7,
                        "amai": 1,
                    }),
                }),
                "aivis": MappingProxyType({
                    "url": os.environ.get("AIVIS_URL", "http://127.0.0.1:10101"),
                    "default_speaker": 1512153250,
                    "speakers": MappingProxyType({
                        "anneli_normal": 888753760,
                        "mai": 1431611904,
                        "chuunibyou": 604166016,
                        "zunda_normal": 1512153250,
                    }),
                }),
            }),
            command_prefix=os.environ.get("COMMAND_PREFIX", "!tts"),
            max_message_length=_env_to_int("MAX_MESSAGE_LENGTH", 10000),
            message_queue_size=_env_to_int("MESSAGE_QUEUE_SIZE", 10),
            reconnect_delay=_env_to_int("RECONNECT_DELAY", 5),
            audio_sample_rate=48000,
            audio_channels=2,
            audio_frame_duration=20,
            rate_limit_messages=_env_to_int("RATE_LIMIT_MESSAGES", 100),
            rate_limit_period=_env_to_int("RATE_LIMIT_PERIOD", 60),
            log_level=os.environ.get("LOG_LEVEL", "DEBUG").upper(),
            log_file=os.environ.get("LOG_FILE", "discord_bot_error.log") or None,
            debug=os.environ.get("DEBUG", "false").lower() in ["true", "1", "yes"],
            test_mode=os.environ.get("TEST_MODE", "false").lower() in ["true", "1", "yes"],
            enable_self_message_processing=os.environ.get("ENABLE_SELF_MESSAGE_PROCESSING", "false").lower() in ["true", "1", "yes"],
        )
