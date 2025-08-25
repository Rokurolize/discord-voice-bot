"""Configuration management for Discord Voice TTS Bot."""

import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv


class Config:
    """Configuration manager for the Discord Voice TTS Bot."""

    def __init__(self) -> None:
        """Initialize configuration from environment variables."""
        # Load environment variables in the correct order
        # 1. Load secrets file first (production)
        secrets_path = os.environ.get("SECRETS_FILE", "~/.config/discord-voice-bot/secrets.env")
        secrets_file = Path(secrets_path).expanduser()
        if secrets_file.exists():
            _ = load_dotenv(secrets_file)

        # 2. Load local .env file (development/testing) - this overrides secrets
        local_env = Path(".env")
        if local_env.exists():
            _ = load_dotenv(local_env)

        # Now read the configuration values after .env is loaded
        self._load_config_values()

    def _load_config_values(self) -> None:
        """Load configuration values from environment variables."""
        # Discord Configuration
        self.discord_token: str = self._get_required_env("DISCORD_BOT_TOKEN")
        self.target_guild_id: int = int(os.environ.get("TARGET_GUILD_ID") or os.environ.get("GUILD_ID") or "1141224103580274760")
        self.target_voice_channel_id: int = int(os.environ.get("TARGET_VOICE_CHANNEL_ID") or os.environ.get("VOICE_CHANNEL_ID") or "1350964414286921749")

        # TTS Configuration
        self.tts_engine: str = os.environ.get("TTS_ENGINE", "voicevox").lower()
        self.tts_speaker: str = os.environ.get("TTS_SPEAKER", "normal").lower()

        # Engine configurations
        self.engines: dict[str, dict[str, Any]] = {
            "voicevox": {
                "url": os.environ.get("VOICEVOX_URL", "http://localhost:50021"),
                "default_speaker": 3,  # Zundamon (Normal)
                "speakers": {
                    "normal": 3,  # Zundamon (Normal)
                    "sexy": 5,  # Zundamon (Seductive)
                    "tsun": 7,  # Zundamon (Tsundere)
                    "amai": 1,  # Zundamon (Sweet)
                },
            },
            "aivis": {
                "url": os.environ.get("AIVIS_URL", "http://127.0.0.1:10101"),
                "default_speaker": 1512153250,  # Unofficial Zundamon (Normal)
                "speakers": {
                    # Anneli voices
                    "anneli_normal": 888753760,  # Anneli (Normal)
                    "anneli_normal2": 888753761,  # Anneli (Standard)
                    "anneli_tension": 888753762,  # Anneli (High Tension)
                    "anneli_calm": 888753763,  # Anneli (Calm)
                    "anneli_happy": 888753764,  # Anneli (Happy)
                    "anneli_angry": 888753765,  # Anneli (Angry/Sad)
                    # Mai voice
                    "まい": 1431611904,  # Mai (Normal)
                    # Chuunibyou voice
                    "中2": 604166016,  # Chuunibyou (Normal)
                    # Unofficial Zundamon voices
                    "zunda_reading": 1512153248,  # Unofficial Zundamon (Reading)
                    "zunda_normal": 1512153250,  # Unofficial Zundamon (Normal)
                    "zunda_amai": 1512153249,  # Unofficial Zundamon (Sweet)
                    "zunda_sexy": 1512153251,  # Unofficial Zundamon (Seductive)
                    "zunda_tsun": 1512153252,  # Unofficial Zundamon (Tsundere)
                    "zunda_whisper": 1512153253,  # Unofficial Zundamon (Whisper)
                    "zunda_hisohiso": 1512153254,  # Unofficial Zundamon (Murmur)
                },
            },
        }

        # Bot Configuration
        self.command_prefix: str = os.environ.get("COMMAND_PREFIX", "!tts")
        self.max_message_length: int = int(os.environ.get("MAX_MESSAGE_LENGTH", "10000"))
        self.message_queue_size: int = int(os.environ.get("MESSAGE_QUEUE_SIZE", "10"))
        self.reconnect_delay: int = int(os.environ.get("RECONNECT_DELAY", "5"))

        # Audio Configuration
        self.audio_sample_rate: int = 48000  # Discord requires 48kHz
        self.audio_channels: int = 2  # Stereo
        self.audio_frame_duration: int = 20  # ms

        # Rate Limiting (very generous to allow natural conversation)
        self.rate_limit_messages: int = int(os.environ.get("RATE_LIMIT_MESSAGES", "100"))
        self.rate_limit_period: int = int(os.environ.get("RATE_LIMIT_PERIOD", "60"))  # seconds

        # Logging Configuration
        self.log_level: str = os.environ.get("LOG_LEVEL", "DEBUG").upper()  # Force DEBUG for full logging
        self.log_file: str | None = os.environ.get("LOG_FILE", "discord_bot_error.log")  # Default error log file

        # Development Configuration
        debug_value = os.environ.get("DEBUG", "false").lower()
        self.debug: bool = debug_value == "true" or debug_value == "1"

        # Test Configuration
        test_value = os.environ.get("TEST_MODE", "false").lower()
        self.test_mode: bool = test_value == "true" or test_value == "1"

        # Self-message Processing Configuration
        self.enable_self_message_processing: bool = os.environ.get("ENABLE_SELF_MESSAGE_PROCESSING", "false").lower() == "true"

    def _get_required_env(self, key: str) -> str:
        """Get required environment variable or raise error."""
        value = os.environ.get(key)
        if not value:
            raise ValueError(f"Required environment variable {key} is not set")
        return value

    @property
    def engine_config(self) -> dict[str, Any]:
        """Get current TTS engine configuration."""
        return self.engines.get(self.tts_engine, self.engines["voicevox"])

    @property
    def api_url(self) -> str:
        """Get TTS API URL for current engine."""
        return self.engine_config["url"]

    @property
    def speaker_id(self) -> int:
        """Get speaker ID for current engine and speaker setting."""
        speakers = self.engine_config["speakers"]
        return speakers.get(self.tts_speaker, self.engine_config["default_speaker"])

    def get_intents(self) -> Any:
        """Get Discord intents required for the bot."""
        import discord

        intents = discord.Intents.default()
        intents.message_content = True  # Required to read message content
        intents.voice_states = True  # Required for voice state updates
        intents.guilds = True  # Required for guild information
        return intents

    def validate(self) -> None:
        """Validate configuration settings."""
        # Check TTS engine
        if self.tts_engine not in self.engines:
            raise ValueError(f"Invalid TTS engine: {self.tts_engine}")

        # Check speaker
        engine_speakers = self.engine_config["speakers"]
        if self.tts_speaker not in engine_speakers:
            raise ValueError(f"Invalid speaker '{self.tts_speaker}' for engine '{self.tts_engine}'")

        # Check numeric values
        if self.target_voice_channel_id <= 0:
            raise ValueError("Invalid voice channel ID")

        if self.max_message_length <= 0:
            raise ValueError("Max message length must be positive")

        if self.message_queue_size <= 0:
            raise ValueError("Message queue size must be positive")


def get_config() -> Config:
    """Return a new Config instance with proper initialization."""
    return Config()


# Config class loads environment variables on initialization
# Use get_config() to get a new instance with proper initialization
