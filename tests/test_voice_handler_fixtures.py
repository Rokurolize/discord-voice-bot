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
    mock_config_manager: FakeConfigManager,
    mock_tts_client: TTSClient,
) -> OldVoiceHandler:
    """Create an old VoiceHandler instance."""
    # OldVoiceHandler expects (bot_client, config_manager) only
    handler = OldVoiceHandler(mock_bot_client, mock_config_manager)
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
    # Work around for HealthMonitor requiring TTS client parameter
    from discord_voice_bot.voice.connection_manager import VoiceConnectionManager
    from discord_voice_bot.voice.health_monitor import HealthMonitor as HealthMonitorReal

    # Create handler manually to pass tts_client to HealthMonitor
    handler = object.__new__(NewVoiceHandler)
    handler.bot = mock_bot_client_real
    handler.config = mock_config

    # Initialize manager components with proper dependencies
    from discord_voice_bot.config_manager import ConfigManagerImpl
    from discord_voice_bot.voice.queue_manager import QueueManager
    from discord_voice_bot.voice.rate_limiter_manager import RateLimiterManager
    from discord_voice_bot.voice.stats_tracker import StatsTracker
    from discord_voice_bot.voice.task_manager import TaskManager

    cfg_manager = ConfigManagerImpl(mock_config)

    handler.connection_manager = VoiceConnectionManager(mock_bot_client_real, cfg_manager)
    handler.queue_manager = QueueManager()
    handler.rate_limiter_manager = RateLimiterManager()
    handler.stats_tracker = StatsTracker()
    handler.task_manager = TaskManager()
    handler.health_monitor = HealthMonitorReal(handler.connection_manager, cfg_manager, mock_tts_client)

    # Set remaining attributes for backward compatibility
    handler.is_playing = False
    handler._last_connection_attempt = handler.connection_manager.last_connection_attempt
    handler._reconnection_cooldown = handler.connection_manager.reconnection_cooldown
    handler.tasks = handler.task_manager.tasks
    handler.voice_client = handler.connection_manager.voice_client
    handler.target_channel = handler.connection_manager.target_channel
    handler.connection_state = handler.connection_manager.connection_state
    handler.synthesis_queue = handler.queue_manager.synthesis_queue
    handler.audio_queue = handler.queue_manager.audio_queue
    handler.current_group_id = handler.queue_manager.current_group_id
    handler.stats = handler.stats_tracker
    handler.rate_limiter = handler.rate_limiter_manager.rate_limiter
    handler.circuit_breaker = handler.rate_limiter_manager.circuit_breaker

    # Initialize worker attributes that cleanup() expects
    handler._synthesizer_worker = None
    handler._player_worker = None

    try:
        yield handler
    finally:
        # Clean up resources for new handler
        await handler.cleanup()


# Import dataclasses after definition
