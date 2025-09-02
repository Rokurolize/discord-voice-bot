"""Fixtures for VoiceHandler tests."""

import dataclasses
import inspect
from typing import Any
from unittest.mock import MagicMock

import pytest
import pytest_asyncio

from discord_voice_bot.config import Config
from discord_voice_bot.tts_client import TTSClient
from discord_voice_bot.voice.handler import VoiceHandler as NewVoiceHandler
from discord_voice_bot.voice_handler import VoiceHandler as OldVoiceHandler

# Type aliases for better readability
OldVoiceHandlerFixture = OldVoiceHandler
NewVoiceHandlerFixture = NewVoiceHandler


@dataclasses.dataclass(frozen=True)
class AudioItem:
    """Mock AudioItem for testing."""

    text: str
    user_id: int
    username: str
    group_id: str
    priority: int = 0
    chunk_index: int = 0
    audio_size: int = 0
    created_at: float | None = None
    processed_at: float | None = None


class FakeConfigManager:
    """A fake config manager for testing."""

    def get_tts_engine(self) -> str:
        """
        Return the name of the TTS engine to use for tests.

        Returns:
            str: Fixed engine identifier "voicevox".
        """
        return "voicevox"

    def get_engines(self) -> dict[str, Any]:
        """
        Return the available TTS engine configurations used by tests.

        Returns:
            dict[str, Any]: A mapping of engine names to their configuration dictionaries.
            For the test fixture this contains a single "voicevox" entry with keys:
              - "url" (str): base URL of the engine service.
              - "default_speaker" (int): default speaker ID.
              - "speakers" (dict[str, int]): named speaker IDs available for tests.
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
        Return the audio sample rate used for generated audio.

        Returns:
            int: Sample rate in hertz (24000).
        """
        return 24000

    def get_audio_channels(self) -> int:
        """
        Return the configured number of audio channels.

        For this test double, always returns 1 (mono).
        """
        return 1

    def get_log_level(self) -> str:
        """
        Return the fixed log level used by the fake configuration manager.

        This test helper always reports "INFO" to simulate a default/non-verbose logging level.

        Returns:
            str: The log level string "INFO".
        """
        return "INFO"

    def get_discord_token(self) -> str:
        """
        Return the Discord token used by tests.

        This test double returns a fixed token ("test_token") for use in fixtures and unit tests.

        Returns:
            str: Discord bot token for tests ("test_token").
        """
        return "test_token"

    def get_target_guild_id(self) -> int:
        """
        Return the fixed Discord guild (server) ID used by tests.

        This test double always returns the constant integer 123456789.
        """
        return 123456789

    def get_target_voice_channel_id(self) -> int:
        """
        Return the fixed test target voice channel ID.

        This configuration shim returns a constant voice channel ID (987654321) used by tests to simulate a target voice channel.
        Returns:
            int: The test voice channel ID.
        """
        return 987654321

    def get_command_prefix(self) -> str:
        """
        Return the command prefix used to trigger text-to-speech commands.

        Returns:
            str: The command prefix string (\"!tts\").
        """
        return "!tts"

    def get_engine_config(self, name: str | None = None) -> dict[str, Any]:
        """
        Return the engine configuration for the given engine name or the currently selected TTS engine.

        If `name` is provided, its configuration is returned; otherwise the configuration for
        self.get_tts_engine() is returned.

        Parameters:
            name (str | None): Optional engine name. If None, uses the configured current TTS engine.

        Returns:
            dict[str, Any]: Configuration dictionary for the requested engine.

        Raises:
            KeyError: If the requested engine name is not present in the engines mapping.
        """
        engines = self.get_engines()
        return engines[name or self.get_tts_engine()]

    def get_max_message_length(self) -> int:
        """
        Return the maximum allowed length for TTS messages in tests.

        This test double returns a fixed value (200) representing the configured
        maximum number of characters permitted in a single message.
        """
        return 200

    def get_message_queue_size(self) -> int:
        """
        Return the maximum number of messages allowed in the message queue for tests.

        This test double always returns 10.
        """
        return 10

    def get_reconnect_delay(self) -> int:
        """
        Return the configured reconnect delay in seconds.

        This value is used as the number of seconds to wait before attempting to reconnect.
        Returns:
            int: Reconnect delay in seconds.
        """
        return 5

    def get_rate_limit_messages(self) -> int:
        """
        Return the maximum number of messages allowed in a rate-limit window.

        Used by tests to determine how many messages can be processed within the configured rate limit period. Returns 50 by default.

        Returns:
            int: Maximum number of messages permitted in the rate limit period.
        """
        return 50

    def get_rate_limit_period(self) -> int:
        """
        Return the rate-limit period, in seconds, used for counting messages in the rate limiter.

        Returns:
            int: Number of seconds for the rate-limit window (always 1).
        """
        return 1

    def get_log_file(self) -> str | None:
        """
        Return the configured log file path.

        Returns:
            str | None: The file path to write logs to, or None when no log file is configured (logs should go to stdout/stderr).
        """
        return None

    def is_debug(self) -> bool:
        """
        Whether debug mode is enabled.

        In this test implementation the value is fixed to False.
        Returns:
            bool: False
        """
        return False

    def get_enable_self_message_processing(self) -> bool:
        """
        Return whether the system should process messages sent by the bot itself.

        Returns:
            bool: False in this test double (self-message processing disabled).
        """
        return False

    def is_test_mode(self) -> bool:
        """
        Return whether the application is running in test mode.

        Always returns True for the test config manager to signal tests should run in test mode.
        """
        return True


@pytest.fixture
def mock_bot_client() -> MagicMock:
    """Create a mock bot client."""
    bot = MagicMock()
    bot.get_channel = MagicMock()
    return bot


@pytest.fixture(scope="module")
def mock_config_manager() -> FakeConfigManager:
    """
    Return a FakeConfigManager preconfigured with deterministic test values.

    Returns:
        FakeConfigManager: A test double that supplies fixed configuration values (e.g., engine, audio settings,
        IDs, and feature flags) for use in unit tests.
    """
    return FakeConfigManager()


@pytest.fixture(scope="module")
def mock_config() -> Config:
    """
    Return a Config instance pre-populated for tests of the new VoiceHandler.

    The returned Config is a concrete, test-oriented configuration with realistic defaults
    (Discord IDs, audio settings, engine entries, and rate limits). The function uses
    dataclasses.replace to ensure `tts_engine` and `engines` are set to the test-specific
    "voicevox" values expected by the new VoiceHandler.

    Returns:
        Config: A Config dataclass populated with test values (audio, engine, rate limits,
        logging, and feature flags) suitable for constructing a NewVoiceHandler in tests.
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
@pytest_asyncio.fixture
async def mock_tts_client(mock_config: Config) -> TTSClient:
    """
    Async pytest fixture that provides a TTSClient instance for tests and ensures it is closed on teardown.

    Yields:
        TTSClient: A test TTS client constructed with the provided Config.

    Teardown:
        Attempts to close the client by calling `aclose()` if available, otherwise `close()`.
        If the close call returns an awaitable, it will be awaited to ensure graceful shutdown.
    """
    client = TTSClient(mock_config)
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
    Async pytest fixture that creates and yields an OldVoiceHandler for tests.

    Yields an initialized OldVoiceHandler configured with the provided test doubles.
    Ensures the handler's resources and background tasks are cleaned up by awaiting
    handler.cleanup() when the fixture is torn down.
    """
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
    Provide an async pytest fixture that yields a NewVoiceHandler instance and ensures it is cleaned up.

    This fixture constructs a NewVoiceHandler with the provided test bot client, config, and TTS client,
    yields it for use in tests, and always awaits handler.cleanup() on teardown to close internal resources.
    """
    handler = NewVoiceHandler(mock_bot_client_real, mock_config, mock_tts_client)
    try:
        yield handler
    finally:
        await handler.cleanup()


# Import dataclasses after definition
