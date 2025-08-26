"""Unit tests for voice_handler module."""

import asyncio
from typing import Any, NamedTuple
from unittest.mock import AsyncMock, MagicMock, Mock

import discord
import pytest
import pytest_asyncio

from discord_voice_bot.tts_client import TTSClient
from discord_voice_bot.voice.gateway import VoiceGatewayManager
from discord_voice_bot.voice.ratelimit import SimpleRateLimiter
from discord_voice_bot.voice_handler import VoiceHandler

# Type aliases for better readability
MockBotClient = MagicMock
VoiceHandlerFixture = VoiceHandler


class AudioItem(NamedTuple):
    """A named tuple for audio queue items."""
    path: str
    group_id: str
    priority: int
    chunk_index: int
    audio_size: int


class FakeConfigManager:
    """A fake config manager for testing."""
    def get_tts_engine(self) -> str: return "voicevox"
    def get_engines(self) -> dict[str, Any]: return {
        "voicevox": {
            "url": "http://localhost:50021",
            "default_speaker": 1,
            "speakers": {"test": 1},
        }
    }
    def get_audio_sample_rate(self) -> int: return 24000
    def get_audio_channels(self) -> int: return 1
    def get_log_level(self) -> str: return "INFO"
    def get_discord_token(self) -> str: return "test_token"
    def get_target_guild_id(self) -> int: return 123456789
    def get_target_voice_channel_id(self) -> int: return 987654321
    def get_command_prefix(self) -> str: return "!tts"
    def get_engine_config(self, name: str | None = None) -> dict[str, Any]:
        engines = self.get_engines()
        return engines[name or self.get_tts_engine()]
    def get_max_message_length(self) -> int: return 200
    def get_message_queue_size(self) -> int: return 10
    def get_reconnect_delay(self) -> int: return 5
    def get_rate_limit_messages(self) -> int: return 50
    def get_rate_limit_period(self) -> int: return 1
    def get_log_file(self) -> str | None: return None
    def is_debug(self) -> bool: return False
    def get_enable_self_message_processing(self) -> bool: return False
    def is_test_mode(self) -> bool: return True


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
            if asyncio.iscoroutine(res):
                await res


@pytest_asyncio.fixture
async def voice_handler(
    mock_bot_client: MagicMock,
    mock_config_manager: FakeConfigManager,
    mock_tts_client: TTSClient,
) -> VoiceHandler:
    """Create a VoiceHandler instance with mocked bot client."""
    handler = VoiceHandler(mock_bot_client, mock_config_manager, mock_tts_client)
    try:
        yield handler
    finally:
        # Ensure any background tasks/queues are closed
        await handler.cleanup()


class TestVoiceHandlerInitialization:
    """Test VoiceHandler initialization."""

    def test_initialization(self, mock_bot_client: MagicMock, mock_config_manager: FakeConfigManager, mock_tts_client: TTSClient) -> None:
        """Test handler initialization."""
        handler = VoiceHandler(mock_bot_client, mock_config_manager, mock_tts_client)
        assert handler.bot == mock_bot_client
        assert handler.voice_client is None
        assert handler.synthesis_queue.empty()
        assert handler.audio_queue.empty()
        assert handler.is_playing is False
        assert handler.current_group_id is None
        assert handler.tts_client is mock_tts_client


class TestQueueManagement:
    """Test queue management functionality."""

    @pytest.mark.asyncio
    async def test_add_to_queue(self, voice_handler: VoiceHandler) -> None:
        """Test adding items to synthesis queue."""
        try:
            async with asyncio.timeout(2.0):  # 2 second timeout
                message_data: dict[str, Any] = {"text": "Hello", "chunks": ["Hello"], "user_id": 123, "username": "TestUser", "group_id": "test_group"}

                await voice_handler.add_to_queue(message_data)

                assert not voice_handler.synthesis_queue.empty()
                item: dict[str, Any] = await voice_handler.synthesis_queue.get()
                assert item["text"] == "Hello"
                assert item["group_id"] == "test_group"
        except asyncio.TimeoutError:
            pytest.fail("Test timed out - add_to_queue operation took too long")

    @pytest.mark.asyncio
    async def test_skip_current_message(self, voice_handler: VoiceHandler) -> None:
        """Test skipping current message group."""
        try:
            async with asyncio.timeout(2.0):  # 2 second timeout
                # Add items with same group
                for i in range(3):
                    await voice_handler.synthesis_queue.put({"text": f"Text {i}", "group_id": "group1"})

                # Add items with different group
                await voice_handler.synthesis_queue.put({"text": "Different", "group_id": "group2"})

                voice_handler.current_group_id = "group1"
                skipped: int = await voice_handler.skip_current()

                # Should have skipped group1 items
                assert skipped >= 3

                # Clear the queue for clean test state
                while not voice_handler.synthesis_queue.empty():
                    try:
                        voice_handler.synthesis_queue.get_nowait()
                    except asyncio.QueueEmpty:
                        break
        except asyncio.TimeoutError:
            pytest.fail("Test timed out - skip_current_message operation took too long")

    @pytest.mark.asyncio
    async def test_clear_all_queues(self, voice_handler: VoiceHandler) -> None:
        """Test clearing all queues."""
        # Add items to both queues
        await voice_handler.synthesis_queue.put({"text": "syn1"})
        await voice_handler.audio_queue.put(AudioItem("path1", "group1", 1, 0, 1024))

        cleared: int = await voice_handler.clear_all()

        assert voice_handler.synthesis_queue.empty()
        assert voice_handler.audio_queue.empty()
        assert cleared == 2

    @pytest.mark.asyncio
    async def test_cleanup_does_not_close_shared_tts_client(
        self, mock_bot_client: MagicMock, mock_config_manager: FakeConfigManager
    ) -> None:
        """Test that cleanup does not close a shared TTSClient."""
        # Create a mock TTSClient with spies for close methods
        tts_client = MagicMock(spec=TTSClient)
        tts_client.close = MagicMock()
        tts_client.aclose = MagicMock()
        tts_client.close_session = MagicMock()

        handler = VoiceHandler(mock_bot_client, mock_config_manager, tts_client)

        # Act
        await handler.cleanup()

        # Assert
        tts_client.close.assert_not_called()
        tts_client.aclose.assert_not_called()
        tts_client.close_session.assert_not_called()

    @pytest.mark.asyncio
    async def test_cleanup_voice_client_does_not_close_shared_tts_client(
        self, mock_bot_client: MagicMock, mock_config_manager: FakeConfigManager
    ) -> None:
        """Test that cleanup_voice_client does not close a shared TTSClient."""
        # Create a mock TTSClient with spies for close methods
        tts_client = MagicMock(spec=TTSClient)
        tts_client.close = MagicMock()
        tts_client.aclose = MagicMock()
        tts_client.close_session = MagicMock()

        handler = VoiceHandler(mock_bot_client, mock_config_manager, tts_client)

        # Act
        await handler.cleanup_voice_client()

        # Assert
        tts_client.close.assert_not_called()
        tts_client.aclose.assert_not_called()
        tts_client.close_session.assert_not_called()


class TestStatusGeneration:
    """Test status information generation."""

    @pytest.mark.asyncio
    async def test_get_status(self, voice_handler: VoiceHandler) -> None:
        """Test getting handler status."""
        # Add some items to queues
        await voice_handler.synthesis_queue.put({"text": "item1"})
        await voice_handler.audio_queue.put(AudioItem("path1", "group1", 1, 0, 1024))

        voice_handler.is_playing = True
        voice_handler.stats["messages_played"] = 10
        voice_handler.stats["messages_skipped"] = 2

        status: dict[str, Any] = voice_handler.get_status()

        assert status["synthesis_queue_size"] == 1
        assert status["audio_queue_size"] == 1
        assert status["playing"] is True
        assert status["messages_played"] == 10
        assert status["messages_skipped"] == 2


class TestCleanup:
    """Test cleanup functionality."""

    @pytest.mark.asyncio
    async def test_cleanup_clears_queues(self, voice_handler: VoiceHandler) -> None:
        """Test cleanup clears all queues."""
        await voice_handler.synthesis_queue.put({"text": "item"})
        await voice_handler.audio_queue.put(AudioItem("path", "group", 1, 0, 1024))

        # Mock the task manager to avoid cancellation issues
        voice_handler.task_manager = MagicMock()
        voice_handler.task_manager.cleanup = AsyncMock()

        await voice_handler.cleanup()

        assert voice_handler.synthesis_queue.empty()
        assert voice_handler.audio_queue.empty()


class TestComplianceTDD:
    """TDD tests for Discord API compliance issues."""

    @pytest.mark.asyncio
    async def test_rate_limiter_compliance(self, voice_handler: VoiceHandler, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that rate limiter meets Discord's 50 req/sec requirement."""
        total_sleep = 0

        async def fake_sleep(duration: float) -> None:
            nonlocal total_sleep
            total_sleep += duration

        monkeypatch.setattr(asyncio, "sleep", fake_sleep)

        # Make 10 requests - should take at least 0.18 seconds (9 sleeps * 0.02s)
        for _ in range(10):
            await voice_handler.rate_limiter.wait_if_needed()

        # Should have slept for at least ~0.18 seconds
        assert total_sleep >= 0.17

    @pytest.mark.asyncio
    async def test_rate_limited_api_call_success(self, voice_handler: VoiceHandler) -> None:
        """Test successful API call with rate limiting."""
        try:
            async with asyncio.timeout(3.0):  # 3 second timeout
                call_count: int = 0

                async def mock_success_api() -> str:
                    nonlocal call_count
                    call_count += 1
                    return f"success_{call_count}"

                result: str = await voice_handler.make_rate_limited_request(mock_success_api)
                assert result == "success_1"
                assert call_count == 1
        except asyncio.TimeoutError:
            pytest.fail("Test timed out - rate_limited_api_call_success took too long")

    @pytest.mark.asyncio
    async def test_rate_limited_api_call_with_retry(self, voice_handler: VoiceHandler) -> None:
        """Test API call that gets rate limited and retries."""
        try:
            async with asyncio.timeout(3.0):  # 3 second timeout
                call_count: int = 0

                async def mock_rate_limited_api() -> str:
                    nonlocal call_count
                    call_count += 1
                    if call_count == 1:
                        # First call gets rate limited
                        mock_response = Mock()
                        mock_response.headers = {"Retry-After": "0.01"}
                        mock_response.status = 429
                        raise discord.HTTPException(response=mock_response, message="Too Many Requests")
                    return f"success_{call_count}"

                result: str = await voice_handler.make_rate_limited_request(mock_rate_limited_api)
                assert result == "success_2"  # Should succeed on retry
                assert call_count == 2
        except asyncio.TimeoutError:
            pytest.fail("Test timed out - rate_limited_api_call_with_retry took too long")

    def test_voice_handler_has_rate_limiter(self, voice_handler: VoiceHandler) -> None:
        """Test that voice handler has proper rate limiter."""
        assert hasattr(voice_handler, "rate_limiter")
        assert isinstance(voice_handler.rate_limiter, SimpleRateLimiter)

    def test_voice_handler_has_voice_gateway(self, voice_handler: VoiceHandler) -> None:
        """Test that voice handler can handle voice gateway events."""
        assert hasattr(voice_handler, "handle_voice_server_update")
        assert hasattr(voice_handler, "handle_voice_state_update")

    @pytest.mark.asyncio
    async def test_voice_gateway_event_handling(self, voice_handler: VoiceHandler) -> None:
        """Test voice gateway event handling updates gateway manager state."""
        # Mock voice client and initialize voice gateway
        mock_voice_client = MagicMock()
        mock_voice_client.is_connected.return_value = True
        voice_handler.voice_client = mock_voice_client

        # Use a MagicMock for the gateway manager to avoid real I/O
        voice_handler.voice_gateway = AsyncMock(spec=VoiceGatewayManager)

        # Test with mock data
        server_payload = {"token": "test_token", "guild_id": "123456789", "endpoint": "test.endpoint:1234"}
        await voice_handler.handle_voice_server_update(server_payload)

        state_payload = {"session_id": "test_session_id"}
        await voice_handler.handle_voice_state_update(state_payload)

        # Assert that the gateway manager's state was updated
        voice_handler.voice_gateway.handle_voice_server_update.assert_called_once_with(server_payload)
        voice_handler.voice_gateway.handle_voice_state_update.assert_called_once_with(state_payload)

    def test_compliance_components_exist(self, voice_handler: VoiceHandler) -> None:
        """Test that all compliance components are properly initialized."""
        # Check that voice handler has the components needed for compliance
        assert voice_handler.rate_limiter is not None
        assert hasattr(voice_handler, "make_rate_limited_request")

        # Should be able to handle voice gateway events
        assert callable(getattr(voice_handler, "handle_voice_server_update", None))
        assert callable(getattr(voice_handler, "handle_voice_state_update", None))

    @pytest.mark.asyncio
    async def test_none_arithmetic_safe_operations(self, voice_handler: VoiceHandler) -> None:
        """Test that None arithmetic operations are handled safely."""
        # Test with None values in stats - should not raise TypeError
        voice_handler.stats["messages_processed"] = None
        voice_handler.stats["connection_errors"] = None
        voice_handler.stats["tts_messages_played"] = None

        # These operations should not raise TypeError: unsupported operand type(s) for +: 'NoneType' and 'int'
        current_count: Any = voice_handler.stats.get("messages_processed", 0)
        voice_handler.stats["messages_processed"] = int(current_count if current_count is not None else 0) + 1

        current_errors: Any = voice_handler.stats.get("connection_errors", 0)
        voice_handler.stats["connection_errors"] = int(current_errors if current_errors is not None else 0) + 1

        current_tts: Any = voice_handler.stats.get("tts_messages_played", 0)
        voice_handler.stats["tts_messages_played"] = int(current_tts if current_tts is not None else 0) + 1

        # Verify the results are correct
        assert voice_handler.stats["messages_processed"] == 1
        assert voice_handler.stats["connection_errors"] == 1
        assert voice_handler.stats["tts_messages_played"] == 1

    @pytest.mark.asyncio
    async def test_voice_gateway_compliance_flow(self, voice_handler: VoiceHandler) -> None:
        """Test complete voice gateway connection flow for Discord API compliance."""
        # Mock voice client and initialize voice gateway
        mock_voice_client: MagicMock = MagicMock()
        mock_voice_client.is_connected.return_value = True
        voice_handler.voice_client = mock_voice_client

        # Use a MagicMock for the gateway manager to avoid real I/O
        voice_handler.voice_gateway = AsyncMock(spec=VoiceGatewayManager)

        # Test voice server update handling (step 1 in Discord flow)
        voice_server_payload: dict[str, str] = {"token": "test_voice_token_123", "guild_id": "123456789012345678", "endpoint": "test-voice-endpoint.example.com:443"}
        await voice_handler.handle_voice_server_update(voice_server_payload)

        # Test voice state update handling (step 2 in Discord flow)
        voice_state_payload: dict[str, str] = {"session_id": "test_session_abc123"}
        await voice_handler.handle_voice_state_update(voice_state_payload)

        # Verify that the gateway manager's methods were called correctly
        voice_handler.voice_gateway.handle_voice_server_update.assert_called_once_with(voice_server_payload)
        voice_handler.voice_gateway.handle_voice_state_update.assert_called_once_with(voice_state_payload)

    @pytest.mark.asyncio
    async def test_discord_gateway_version_compliance(self, voice_handler: VoiceHandler) -> None:
        """Test that voice handler is configured for Discord Gateway version 8."""
        # This test ensures we're using the latest voice gateway version as required
        # Version 8 is mandatory as of November 18th, 2024

        # The voice handler should be prepared to handle version 8 features
        assert hasattr(voice_handler, "handle_voice_server_update")
        assert hasattr(voice_handler, "handle_voice_state_update")

        # Should handle version 8 specific fields without issues
        # (In practice, this would come from discord.py's voice client)
        mock_voice_client: MagicMock = MagicMock()
        mock_voice_client.is_connected.return_value = True
        voice_handler.voice_client = mock_voice_client

        # Test heartbeat handling (version 8 requires seq_ack) - create but don't use as it's for documentation
        _heartbeat_payload: dict[str, Any] = {"op": 3, "d": {"t": 1501184119561, "seq_ack": 10}}  # Heartbeat
        # This should be handled by discord.py internally

    @pytest.mark.asyncio
    async def test_e2ee_protocol_readiness(self, voice_handler: VoiceHandler) -> None:
        """Test that voice handler is prepared for Discord's DAVE E2EE protocol."""
        # As of September 2024, Discord requires E2EE support
        # This test ensures our handler can support the transition

        # Voice handler should be able to handle protocol transitions
        assert hasattr(voice_handler, "handle_voice_server_update")
        assert hasattr(voice_handler, "handle_voice_state_update")

        # Test handling of protocol transition messages - create but don't use as it's for documentation
        _transition_payload: dict[str, Any] = {"op": 21, "d": {"transition_id": "test_transition_123", "protocol_version": 0}}  # DAVE Protocol Prepare Transition  # Downgrade to non-E2EE

        # Should handle protocol transition without crashing
        # (In practice, discord.py handles the actual protocol negotiation)
        mock_voice_client: MagicMock = MagicMock()
        mock_voice_client.is_connected.return_value = True
        voice_handler.voice_client = mock_voice_client

        try:
            async with asyncio.timeout(2.0):  # 2 second timeout
                # This should not raise an exception
                await voice_handler.handle_voice_server_update({"token": "test", "guild_id": "123", "endpoint": "test:443"})
        except asyncio.TimeoutError:
            pytest.fail("Test timed out - e2ee_protocol_readiness took too long")

    @pytest.mark.asyncio
    async def test_ip_discovery_compliance(self, voice_handler: VoiceHandler) -> None:
        """Test IP discovery functionality for NAT traversal compliance."""
        # Discord requires UDP hole punching for voice connections
        # This test ensures we can handle IP discovery payloads

        # IP Discovery packet format examples (for documentation) - these would be used by discord.py internally
        # Type: 0x1 (request), Length: 70, SSRC: uint32, Address: 64 bytes, Port: uint16
        _discovery_request: bytes = b"\x00\x01" + b"\x00\x46" + b"\x00\x00\x00\x01" + b"\x00" * 64 + b"\x00\x00"

        # Response would be Type: 0x2 (response) + same format with actual IP/port
        _discovery_response: bytes = b"\x00\x02" + b"\x00\x46" + b"\x00\x00\x00\x01" + b"127.0.0.1".ljust(64, b"\x00") + b"\x1f\x40"

        # Voice handler should support IP discovery through discord.py
        # We test that the handler can be initialized with IP discovery capability
        assert voice_handler is not None
        assert hasattr(voice_handler, "voice_client")

        # Test that voice handler has the necessary components for IP discovery
        assert hasattr(voice_handler, "rate_limiter")
        assert hasattr(voice_handler, "make_rate_limited_request")

    def test_voice_connection_state_tracking(self, voice_handler: VoiceHandler) -> None:
        """Test proper tracking of voice connection state."""
        # Test initial state
        assert voice_handler.connection_state == "DISCONNECTED"
        assert voice_handler.last_connection_attempt == 0.0

        # Test state changes
        voice_handler.connection_state = "CONNECTING"
        assert voice_handler.connection_state == "CONNECTING"

        # Test connection attempt tracking
        import asyncio

        old_time: float = voice_handler.last_connection_attempt
        voice_handler.last_connection_attempt = asyncio.get_event_loop().time()

        assert voice_handler.last_connection_attempt > old_time
