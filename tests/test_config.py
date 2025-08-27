"""Tests for Config component - TDD Approach (Red-Green-Refactor)."""

import os
from unittest.mock import patch

import pytest

from discord_voice_bot.config import Config


class TestConfig:
    """Test cases for Config - TDD Approach."""

    @patch("discord_voice_bot.config.Path.exists", return_value=False)
    def test_config_initialization_with_default_env(self, mock_exists) -> None:
        """Test Config initializes with default environment variables."""
        with patch.dict(
            os.environ,
            {"DISCORD_BOT_TOKEN": "test_token", "TARGET_VOICE_CHANNEL_ID": "12345", "TTS_ENGINE": "voicevox", "TTS_SPEAKER": "normal", "MAX_MESSAGE_LENGTH": "5000", "DEBUG": "false"},
            clear=True,
        ):
            config = Config.from_env()

            assert config.discord_token == "test_token"
            assert config.target_voice_channel_id == 12345
            assert config.tts_engine == "voicevox"
            assert config.tts_speaker == "normal"
            assert config.max_message_length == 5000
            assert config.command_prefix == "!tts"
            assert config.audio_sample_rate == 48000
            assert config.audio_channels == 2
            assert config.debug is False

    @patch("discord_voice_bot.config.Path.exists", return_value=False)
    def test_config_initialization_missing_required_env(self, mock_exists) -> None:
        """Test Config returns an empty token when the env var is missing."""
        with patch.dict(os.environ, {}, clear=True):
            config = Config.from_env()
            assert config.discord_token == ""

    @patch("discord_voice_bot.config.Path.exists", return_value=False)
    def test_config_default_values(self, mock_exists) -> None:
        """Test Config uses proper default values."""
        with patch.dict(os.environ, {"DISCORD_BOT_TOKEN": "test_token", "DEBUG": "false"}, clear=True):
            config = Config.from_env()

            # Discord defaults
            assert config.target_voice_channel_id == 0

            # TTS defaults
            assert config.tts_engine == "voicevox"
            assert config.tts_speaker == "normal"

            # Bot defaults
            assert config.command_prefix == "!tts"
            assert config.max_message_length == 10000
            assert config.message_queue_size == 10
            assert config.reconnect_delay == 5

            # Audio defaults
            assert config.audio_sample_rate == 48000
            assert config.audio_channels == 2
            assert config.audio_frame_duration == 20

            # Rate limiting defaults
            assert config.rate_limit_messages == 100
            assert config.rate_limit_period == 60

            # Logging defaults
            assert config.log_level == "DEBUG"
            assert config.log_file == "discord_bot_error.log"

            # Development defaults
            assert config.debug is False
