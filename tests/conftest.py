import dataclasses
import inspect
from typing import Any
from unittest.mock import MagicMock

import pytest

from discord_voice_bot.config import Config
from discord_voice_bot.config_manager import ConfigManagerImpl
from discord_voice_bot.tts_client import TTSClient
from discord_voice_bot.voice.handler import VoiceHandler as NewVoiceHandler
from discord_voice_bot.voice_handler import VoiceHandler as OldVoiceHandler


# VoiceHandler Test Fixtures
class FakeConfigManager:
    """A fake config manager for testing."""

    def get_tts_engine(self) -> str:
        return "voicevox"

    def get_engines(self) -> dict[str, Any]:
        return {
            "voicevox": {
                "url": "http://localhost:50021",
                "default_speaker": 1,
                "speakers": {"test": 1},
            }
        }

    def get_audio_sample_rate(self) -> int:
        return 24000

    def get_audio_channels(self) -> int:
        return 1

    def get_log_level(self) -> str:
        return "INFO"

    def get_discord_token(self) -> str:
        return "test_token"

    def get_target_guild_id(self) -> int:
        return 123456789

    def get_target_voice_channel_id(self) -> int:
        return 987654321

    def get_command_prefix(self) -> str:
        return "!tts"

    def get_engine_config(self, name: str | None = None) -> dict[str, Any]:
        engines = self.get_engines()
        return engines[name or self.get_tts_engine()]

    def get_max_message_length(self) -> int:
        return 200

    def get_message_queue_size(self) -> int:
        return 10

    def get_reconnect_delay(self) -> int:
        return 5

    def get_rate_limit_messages(self) -> int:
        return 50

    def get_rate_limit_period(self) -> int:
        return 1

    def get_log_file(self) -> str | None:
        return None

    def is_debug(self) -> bool:
        return False

    def get_enable_self_message_processing(self) -> bool:
        return False

    def is_test_mode(self) -> bool:
        return True


# Basic fixtures
@pytest.fixture
def mock_bot_client() -> MagicMock:
    """Create a mock bot client."""
    bot = MagicMock()
    bot.get_channel = MagicMock()
    return bot


@pytest.fixture(scope="module")
def mock_config_manager() -> FakeConfigManager:
    """Create a fake config manager."""
    return FakeConfigManager()


@pytest.fixture(scope="module")
def mock_config() -> Config:
    """Create a real Config object for new VoiceHandler."""
    return dataclasses.replace(
        Config(
            discord_token="test_discord_token",
            target_guild_id=987654321,
            target_voice_channel_id=123456789,
            tts_engine="voicevox",
            tts_speaker="normal",
            engines={
                "voicevox": {
                    "url": "http://localhost:50021",
                    "default_speaker": 3,
                    "speakers": {"normal": 3},
                }
            },
            command_prefix="!tts",
            max_message_length=100,
            message_queue_size=10,
            reconnect_delay=5,
            audio_sample_rate=48000,
            audio_channels=2,
            audio_frame_duration=20,
            rate_limit_messages=5,
            rate_limit_period=60,
            log_level="DEBUG",
            log_file=None,
            debug=True,
            test_mode=True,
            enable_self_message_processing=False,
        ),  # Use existing config structure
        tts_engine="voicevox",
        engines={
            "voicevox": {
                "url": "http://localhost:50021",
                "default_speaker": 1,
                "speakers": {"test": 1},
            }
        },
    )


@pytest.fixture
def mock_bot_client_real() -> MagicMock:
    """Create a mock Discord client compatible with new VoiceHandler."""
    return MagicMock()


# Async fixtures for VoiceHandler
import pytest_asyncio


@pytest_asyncio.fixture
async def mock_tts_client(mock_config_manager: FakeConfigManager) -> TTSClient:
    """Create a mock TTS client with proper teardown."""
    client = TTSClient(mock_config_manager)
    try:
        yield client
    finally:
        # Gracefully close resources regardless of the method name/signature
        close = getattr(client, "aclose", None) or getattr(client, "close", None)
        if callable(close):
            res = close()
            if inspect.isawaitable(res):
                await res


@pytest_asyncio.fixture
async def voice_handler_old(
    mock_bot_client: MagicMock,
    mock_config: Config,
    mock_tts_client: TTSClient,
) -> OldVoiceHandler:
    """Create an old VoiceHandler instance."""
    # Prefer passing real Config to avoid env fallback
    handler = OldVoiceHandler(mock_bot_client, mock_config)
    try:
        yield handler
    finally:
        # Ensure any background tasks/queues are closed
        await handler.cleanup()


@pytest_asyncio.fixture
async def voice_handler_new(
    mock_bot_client_real: MagicMock,
    mock_config: Config,
    mock_tts_client: TTSClient,
) -> NewVoiceHandler:
    """Create a new VoiceHandler instance with proper config."""
    handler = NewVoiceHandler(mock_bot_client_real, mock_config, mock_tts_client)
    try:
        yield handler
    finally:
        await handler.cleanup()


# Type aliases for better readability
OldVoiceHandlerFixture = OldVoiceHandler
NewVoiceHandlerFixture = NewVoiceHandler


@pytest.fixture
def config() -> Config:
    """
    Returns a default, test-safe, immutable Config object.

    Since Config is a frozen dataclass, tests that need to override specific
    values must create a new config object using `dataclasses.replace()`.

    Example:
        new_config = dataclasses.replace(config, tts_engine="aivis")
    """
    return Config(
        discord_token="test_discord_token",
        target_guild_id=987654321,
        target_voice_channel_id=123456789,
        tts_engine="voicevox",
        tts_speaker="normal",
        engines={
            "voicevox": {
                "url": "http://localhost:50021",
                "default_speaker": 3,
                "speakers": {"normal": 3},
            }
        },
        command_prefix="!tts",
        max_message_length=100,
        message_queue_size=10,
        reconnect_delay=5,
        audio_sample_rate=48000,
        audio_channels=2,
        audio_frame_duration=20,
        rate_limit_messages=5,
        rate_limit_period=60,
        log_level="DEBUG",
        log_file=None,
        debug=True,
        test_mode=True,
        enable_self_message_processing=False,
    )


@pytest.fixture
def test_config_manager(mock_env_vars) -> ConfigManagerImpl:
    """Provide a ConfigManagerImpl with TEST_MODE enabled."""
    return ConfigManagerImpl(test_mode=True)


@pytest.fixture
def prod_config_manager(mock_env_vars) -> ConfigManagerImpl:
    """Provide a ConfigManagerImpl reflecting env (TEST_MODE may be false)."""
    return ConfigManagerImpl()


# Global env fixture for performance tests
@pytest.fixture
def mock_env_vars(monkeypatch: pytest.MonkeyPatch) -> None:
    """Set environment variables for tests that depend on runtime config.

    Ensures deterministic, offline-safe defaults.
    """
    monkeypatch.setenv("DISCORD_BOT_TOKEN", "test_token")
    monkeypatch.setenv("TARGET_VOICE_CHANNEL_ID", "123456789")
    monkeypatch.setenv("TTS_ENGINE", "voicevox")
    monkeypatch.setenv("VOICEVOX_URL", "http://localhost:50021")
    monkeypatch.setenv("TEST_MODE", "1")
