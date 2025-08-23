"""Tests for Config component - TDD Approach (Red-Green-Refactor)."""

import os
from unittest.mock import patch

import pytest

from discord_voice_bot.config import Config


class TestConfig:
    """Test cases for Config - TDD Approach."""

    def test_config_initialization_with_default_env(self) -> None:
        """Test Config initializes with default environment variables."""
        with patch.dict(
            os.environ, {"DISCORD_BOT_TOKEN": "test_token", "TARGET_VOICE_CHANNEL_ID": "12345", "TTS_ENGINE": "voicevox", "TTS_SPEAKER": "normal", "MAX_MESSAGE_LENGTH": "5000"}, clear=True
        ):
            config = Config()

            assert config.discord_token == "test_token"
            assert config.target_voice_channel_id == 12345
            assert config.tts_engine == "voicevox"
            assert config.tts_speaker == "normal"
            assert config.max_message_length == 5000
            assert config.command_prefix == "!tts"
            assert config.audio_sample_rate == 48000
            assert config.audio_channels == 2
            assert config.debug is False

    def test_config_initialization_missing_required_env(self) -> None:
        """Test Config raises error when required env var is missing."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="Required environment variable DISCORD_BOT_TOKEN is not set"):
                _ = Config()

    def test_config_default_values(self) -> None:
        """Test Config uses proper default values."""
        with patch.dict(os.environ, {"DISCORD_BOT_TOKEN": "test_token"}, clear=True):
            config = Config()

            # Discord defaults
            assert config.target_voice_channel_id == 1350964414286921749

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
            assert config.log_level == "INFO"
            assert config.log_file is None

            # Development defaults
            assert config.debug is False

    def test_config_engine_configurations(self) -> None:
        """Test Config engine configurations are properly set."""
        with patch.dict(os.environ, {"DISCORD_BOT_TOKEN": "test_token", "TTS_ENGINE": "voicevox"}, clear=True):
            config = Config()

            # Check VoiceVox engine config
            voicevox_config = config.engines["voicevox"]
            assert "url" in voicevox_config
            assert "default_speaker" in voicevox_config
            assert "speakers" in voicevox_config
            assert voicevox_config["default_speaker"] == 3
            assert "normal" in voicevox_config["speakers"]

            # Check Aivis engine config
            aivis_config = config.engines["aivis"]
            assert "url" in aivis_config
            assert "default_speaker" in aivis_config
            assert "speakers" in aivis_config
            assert aivis_config["default_speaker"] == 1512153250
            assert "zunda_normal" in aivis_config["speakers"]

    def test_config_properties(self) -> None:
        """Test Config property accessors."""
        with patch.dict(os.environ, {"DISCORD_BOT_TOKEN": "test_token", "TTS_ENGINE": "voicevox", "TTS_SPEAKER": "normal"}, clear=True):
            config = Config()

            # Test engine_config property
            engine_config = config.engine_config
            assert engine_config == config.engines["voicevox"]

            # Test api_url property
            assert config.api_url == config.engines["voicevox"]["url"]

            # Test speaker_id property
            assert config.speaker_id == config.engines["voicevox"]["speakers"]["normal"]

    def test_config_get_intents(self) -> None:
        """Test Config.get_intents() method."""
        with patch.dict(os.environ, {"DISCORD_BOT_TOKEN": "test_token"}, clear=True):
            config = Config()
            intents = config.get_intents()

            # Check that required intents are set
            assert intents.message_content is True
            assert intents.voice_states is True
            assert intents.guilds is True

    def test_config_validate_valid_config(self) -> None:
        """Test Config.validate() with valid configuration."""
        with patch.dict(
            os.environ,
            {"DISCORD_BOT_TOKEN": "test_token", "TARGET_VOICE_CHANNEL_ID": "12345", "TTS_ENGINE": "voicevox", "TTS_SPEAKER": "normal", "MAX_MESSAGE_LENGTH": "5000", "MESSAGE_QUEUE_SIZE": "5"},
            clear=True,
        ):
            config = Config()
            # Should not raise any exceptions
            config.validate()

    def test_config_validate_invalid_tts_engine(self) -> None:
        """Test Config.validate() with invalid TTS engine."""
        with patch.dict(os.environ, {"DISCORD_BOT_TOKEN": "test_token", "TTS_ENGINE": "invalid_engine"}, clear=True):
            config = Config()
            with pytest.raises(ValueError, match="Invalid TTS engine: invalid_engine"):
                config.validate()

    def test_config_validate_invalid_speaker(self) -> None:
        """Test Config.validate() with invalid speaker."""
        with patch.dict(os.environ, {"DISCORD_BOT_TOKEN": "test_token", "TTS_ENGINE": "voicevox", "TTS_SPEAKER": "invalid_speaker"}, clear=True):
            config = Config()
            with pytest.raises(ValueError, match="Invalid speaker 'invalid_speaker' for engine 'voicevox'"):
                config.validate()

    def test_config_validate_invalid_numeric_values(self) -> None:
        """Test Config.validate() with invalid numeric values."""
        test_cases = [
            ("TARGET_VOICE_CHANNEL_ID", "0", "Invalid voice channel ID"),
            ("TARGET_VOICE_CHANNEL_ID", "-1", "Invalid voice channel ID"),
            ("MAX_MESSAGE_LENGTH", "0", "Max message length must be positive"),
            ("MAX_MESSAGE_LENGTH", "-100", "Max message length must be positive"),
            ("MESSAGE_QUEUE_SIZE", "0", "Message queue size must be positive"),
            ("MESSAGE_QUEUE_SIZE", "-5", "Message queue size must be positive"),
        ]

        for env_var, value, expected_error in test_cases:
            with patch.dict(os.environ, {"DISCORD_BOT_TOKEN": "test_token", env_var: value}, clear=True):
                config = Config()
                with pytest.raises(ValueError, match=expected_error):
                    config.validate()

    def test_config_environment_variable_precedence(self) -> None:
        """Test that environment variables take precedence over defaults."""
        with patch.dict(
            os.environ,
            {
                "DISCORD_BOT_TOKEN": "test_token",
                "VOICE_CHANNEL_ID": "99999",  # Alternative name for target_voice_channel_id
                "TARGET_VOICE_CHANNEL_ID": "12345",  # This should take precedence
                "TTS_ENGINE": "aivis",
                "TTS_SPEAKER": "amai",
                "MAX_MESSAGE_LENGTH": "8000",
                "DEBUG": "true",
            },
            clear=True,
        ):
            config = Config()

            assert config.target_voice_channel_id == 12345  # Should use TARGET_VOICE_CHANNEL_ID
            assert config.tts_engine == "aivis"
            assert config.tts_speaker == "amai"
            assert config.max_message_length == 8000
            assert config.debug is True

    def test_config_debug_flag_parsing(self) -> None:
        """Test Config debug flag parsing."""
        test_cases = [("true", True), ("True", True), ("TRUE", True), ("false", False), ("False", False), ("FALSE", False), ("1", True), ("0", False), ("", False), ("anything_else", False)]

        for debug_value, expected in test_cases:
            with patch.dict(os.environ, {"DISCORD_BOT_TOKEN": "test_token", "DEBUG": debug_value}, clear=True):
                # Force .env loading by setting PYTEST_CURRENT_TEST
                with patch.dict(os.environ, {"PYTEST_CURRENT_TEST": "1"}, clear=False):
                    config = Config()
                    assert config.debug is expected

    def test_config_dotenv_loading(self) -> None:
        """Test Config loads from .env files."""
        with patch.dict(os.environ, {"DISCORD_BOT_TOKEN": "test_token", "PYTEST_CURRENT_TEST": "1"}, clear=True):
            with patch("discord_voice_bot.config.Path.exists", return_value=True), patch("discord_voice_bot.config.load_dotenv") as mock_load_dotenv:
                _ = Config()

                # Should try to load from both secrets file and local .env
                assert mock_load_dotenv.call_count == 2
