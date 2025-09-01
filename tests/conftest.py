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
        """
        Return the default TTS engine name used by the fake config manager for tests.
        
        Returns:
            str: The TTS engine identifier ("voicevox").
        """
        return "voicevox"

    def get_engines(self) -> dict[str, Any]:
        """
        Return available TTS engine configurations.
        
        Returns:
            dict[str, Any]: Mapping of engine name to its configuration. Each engine config contains:
                - "url" (str): base URL of the engine service.
                - "default_speaker" (int): default speaker ID.
                - "speakers" (dict[str, int]): available speaker name → speaker ID mapping.
        
        Example:
            {
                "voicevox": {
                    "url": "http://localhost:50021",
                    "default_speaker": 1,
                    "speakers": {"test": 1},
                }
            }
        """
        return {
            "voicevox": {
                "url": "http://localhost:50021",
                "default_speaker": 1,
                "speakers": {"test": 1},
            }
        }

    def get_audio_sample_rate(self) -> int:
        """
        Return the audio sample rate (Hz) used by the test configuration.
        
        Returns:
            int: Sample rate in Hertz (24000).
        """
        return 24000

    def get_audio_channels(self) -> int:
        """
        Return the number of audio channels used for generated audio.
        
        Returns:
            int: Number of channels (1 for mono).
        """
        return 1

    def get_log_level(self) -> str:
        """
        Return the configured log level for tests.
        
        This fake config manager always returns the fixed log level string "INFO" to provide a deterministic
        logging level for test fixtures.
        
        Returns:
            str: The log level name (always "INFO").
        """
        return "INFO"

    def get_discord_token(self) -> str:
        """
        Return the Discord bot token used in tests.
        
        Returns:
            str: Deterministic test token "test_token".
        """
        return "test_token"

    def get_target_guild_id(self) -> int:
        """
        Return the Discord guild (server) ID used in tests.
        
        Returns:
            int: Deterministic test guild ID 123456789.
        """
        return 123456789

    def get_target_voice_channel_id(self) -> int:
        """
        Return the configured Discord voice channel ID used for tests.
        
        Returns:
            int: The numeric ID of the target voice channel (987654321).
        """
        return 987654321

    def get_command_prefix(self) -> str:
        """
        Return the bot command prefix used for TTS commands in tests.
        
        This fake config manager consistently returns the test prefix "!tts" so tests
        can rely on a stable command trigger for simulating user input.
        """
        return "!tts"

    def get_engine_config(self, name: str | None = None) -> dict[str, Any]:
        """
        Return the configuration dictionary for a named TTS engine or for the current TTS engine.
        
        Parameters:
            name (str | None): Engine name to look up. If None, the currently configured TTS engine name is used.
        
        Returns:
            dict[str, Any]: The engine configuration mapping for the requested engine.
        
        Raises:
            KeyError: If the requested engine name is not present in the engines mapping.
        """
        engines = self.get_engines()
        return engines[name or self.get_tts_engine()]

    def get_max_message_length(self) -> int:
        """
        Return the maximum allowed TTS message length in characters.
        
        Returns:
            int: Maximum number of characters allowed per message (200).
        """
        return 200

    def get_message_queue_size(self) -> int:
        """
        Return the configured maximum number of messages allowed in the voice handler's message queue for tests.
        
        This fake implementation provides a deterministic, test-safe value.
        
        Returns:
            int: Maximum message queue size (10).
        """
        return 10

    def get_reconnect_delay(self) -> int:
        """
        Return the configured delay (in seconds) before attempting to reconnect.
        
        Returns:
            int: Reconnect delay in seconds (default: 5).
        """
        return 5

    def get_rate_limit_messages(self) -> int:
        """
        Return the maximum number of messages allowed in the rate limit window.
        
        This is the test-default rate limit count (50) used by fixtures and handlers.
        
        Returns:
            int: Number of messages permitted per rate limit period.
        """
        return 50

    def get_rate_limit_period(self) -> int:
        """
        Return the rate limit period (in seconds) used for message rate limiting in tests.
        
        Returns:
            int: The duration, in seconds, of the rate limit window (always 1 for the test fake).
        """
        return 1

    def get_log_file(self) -> str | None:
        """
        Return the configured log file path, or None if no log file is configured.
        
        Returns:
            str | None: Path to the log file, or None when logging to a file is not enabled.
        """
        return None

    def is_debug(self) -> bool:
        """
        Return whether debug mode is enabled.
        
        Returns:
            bool: Always False for the fake configuration used in tests.
        """
        return False

    def get_enable_self_message_processing(self) -> bool:
        """
        Whether the bot should process messages it sent itself.
        
        Returns:
            bool: False in test fixtures — self-sent messages are not processed.
        """
        return False

    def is_test_mode(self) -> bool:
        """
        Return whether the configuration is in test mode.
        
        Always returns True for this test-only FakeConfigManager.
        """
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
    """
    Pytest fixture that provides a FakeConfigManager for tests.
    
    Returns:
        FakeConfigManager: A test-only config manager exposing deterministic config values.
    """
    return FakeConfigManager()


@pytest.fixture(scope="module")
def mock_config() -> Config:
    """
    Create a test-safe, real Config instance configured for the new VoiceHandler.
    
    This fixture returns an immutable Config pre-filled with deterministic test values (Discord token, target IDs,
    VoiceVox engine settings, audio and rate-limit defaults). The returned object is suitable for tests that require a
    fully populated Config; since Config is frozen, use dataclasses.replace to create variations for specific tests.
    
    Returns:
        Config: A frozen Config object with VoiceVox set as the TTS engine and test-oriented defaults.
    """
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
    """
    Create and yield a TTSClient for tests, ensuring graceful teardown.
    
    Yields:
        TTSClient: A TTSClient constructed with the provided config manager. On teardown, attempts to call either `aclose` or `close` on the client and awaits the result if it is awaitable.
    """
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
    """
    Create and yield a legacy (old) VoiceHandler instance for tests.
    
    Yields:
        An initialized OldVoiceHandler constructed with the provided bot client and Config.
        The fixture ensures proper teardown by awaiting handler.cleanup() after the test.
    
    Notes:
        The `mock_tts_client` parameter is accepted to ensure the test TTS client is created and torn down
        as part of the fixture dependency graph even though it is not directly used to construct the handler.
    """
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
    """
    Create and yield a NewVoiceHandler wired with the provided bot client, configuration, and TTS client.
    
    Yields:
        NewVoiceHandler: an instantiated handler ready for use in tests.
    
    Teardown:
        Awaits handler.cleanup() to stop background tasks and release resources when the fixture is torn down.
    """
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
    """
    Return a ConfigManagerImpl configured from the current environment (respecting TEST_MODE if set).
    
    This fixture constructs a production-like ConfigManagerImpl that reads configuration from environment variables;
    it does not force test mode on the manager.
    """
    return ConfigManagerImpl()


# Global env fixture for performance tests
@pytest.fixture
def mock_env_vars(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    Set deterministic environment variables used by tests.
    
    Provides offline-safe defaults required by ConfigManagerImpl and other fixtures:
    DISCORD_BOT_TOKEN=test_token, TARGET_VOICE_CHANNEL_ID=123456789, TTS_ENGINE=voicevox,
    VOICEVOX_URL=http://localhost:50021, TEST_MODE=1.
    """
    monkeypatch.setenv("DISCORD_BOT_TOKEN", "test_token")
    monkeypatch.setenv("TARGET_VOICE_CHANNEL_ID", "123456789")
    monkeypatch.setenv("TTS_ENGINE", "voicevox")
    monkeypatch.setenv("VOICEVOX_URL", "http://localhost:50021")
    monkeypatch.setenv("TEST_MODE", "1")
