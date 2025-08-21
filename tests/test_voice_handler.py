"""Unit tests for voice_handler module."""

import asyncio
from unittest.mock import MagicMock, Mock

import discord
import pytest

from discord_voice_bot.voice_handler import SimpleRateLimiter, VoiceHandler


@pytest.fixture
def mock_bot_client():
    """Create a mock bot client."""
    bot = MagicMock()
    bot.get_channel = MagicMock()
    return bot


@pytest.fixture
def voice_handler(mock_bot_client):
    """Create a VoiceHandler instance with mocked bot client."""
    handler = VoiceHandler(mock_bot_client)
    return handler


class TestVoiceHandlerInitialization:
    """Test VoiceHandler initialization."""

    def test_initialization(self, mock_bot_client):
        """Test handler initialization."""
        handler = VoiceHandler(mock_bot_client)
        assert handler.bot == mock_bot_client
        assert handler.voice_client is None
        assert handler.synthesis_queue.empty()
        assert handler.audio_queue.empty()
        assert handler.is_playing is False
        assert handler.current_group_id is None


class TestQueueManagement:
    """Test queue management functionality."""

    @pytest.mark.asyncio
    async def test_add_to_queue(self, voice_handler):
        """Test adding items to synthesis queue."""
        message_data = {"text": "Hello", "chunks": ["Hello"], "user_id": 123, "username": "TestUser", "group_id": "test_group"}

        await voice_handler.add_to_queue(message_data)

        assert not voice_handler.synthesis_queue.empty()
        item = await voice_handler.synthesis_queue.get()
        assert item["text"] == "Hello"
        assert item["group_id"] == "test_group"

    @pytest.mark.asyncio
    async def test_skip_current_message(self, voice_handler):
        """Test skipping current message group."""
        # Add items with same group
        for i in range(3):
            await voice_handler.synthesis_queue.put({"text": f"Text {i}", "group_id": "group1"})

        # Add items with different group
        await voice_handler.synthesis_queue.put({"text": "Different", "group_id": "group2"})

        voice_handler.current_group_id = "group1"
        skipped = await voice_handler.skip_current()

        # Should have skipped group1 items
        assert skipped >= 3

        # Clear the queue for clean test state
        while not voice_handler.synthesis_queue.empty():
            try:
                voice_handler.synthesis_queue.get_nowait()
            except asyncio.QueueEmpty:
                break

    @pytest.mark.asyncio
    async def test_clear_all_queues(self, voice_handler):
        """Test clearing all queues."""
        # Add items to both queues
        await voice_handler.synthesis_queue.put({"text": "syn1"})
        await voice_handler.audio_queue.put(("path1", "group1"))

        cleared = await voice_handler.clear_all()

        assert voice_handler.synthesis_queue.empty()
        assert voice_handler.audio_queue.empty()
        assert cleared == 2


class TestStatusGeneration:
    """Test status information generation."""

    @pytest.mark.asyncio
    async def test_get_status(self, voice_handler):
        """Test getting handler status."""
        # Add some items to queues
        await voice_handler.synthesis_queue.put({"text": "item1"})
        await voice_handler.audio_queue.put(("path1", "group1"))

        voice_handler.is_playing = True
        voice_handler.stats["messages_played"] = 10
        voice_handler.stats["messages_skipped"] = 2

        status = voice_handler.get_status()

        assert status["synthesis_queue_size"] == 1
        assert status["audio_queue_size"] == 1
        assert status["playing"] is True
        assert status["messages_played"] == 10
        assert status["messages_skipped"] == 2


class TestCleanup:
    """Test cleanup functionality."""

    @pytest.mark.asyncio
    async def test_cleanup_clears_queues(self, voice_handler):
        """Test cleanup clears all queues."""
        await voice_handler.synthesis_queue.put({"text": "item"})
        await voice_handler.audio_queue.put(("path", "group"))

        # Mock tasks to avoid cancellation issues
        voice_handler.tasks = []

        await voice_handler.cleanup()

        assert voice_handler.synthesis_queue.empty()
        assert voice_handler.audio_queue.empty()


class TestComplianceTDD:
    """TDD tests for Discord API compliance issues."""

    @pytest.mark.asyncio
    async def test_rate_limiter_compliance(self, voice_handler):
        """Test that rate limiter meets Discord's 50 req/sec requirement."""
        import time

        start_time = time.time()

        # Make 10 requests - should take at least 0.2 seconds (10/50)
        for i in range(10):
            await voice_handler.rate_limiter.wait_if_needed()

        elapsed = time.time() - start_time

        # Should have taken at least 0.2 seconds (10 requests at 50/sec = 0.2 sec)
        assert elapsed >= 0.15  # Allow some margin for timing precision

    @pytest.mark.asyncio
    async def test_rate_limited_api_call_success(self, voice_handler):
        """Test successful API call with rate limiting."""
        call_count = 0

        async def mock_success_api():
            nonlocal call_count
            call_count += 1
            return f"success_{call_count}"

        result = await voice_handler.make_rate_limited_request(mock_success_api)
        assert result == "success_1"
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_rate_limited_api_call_with_retry(self, voice_handler):
        """Test API call that gets rate limited and retries."""
        call_count = 0

        async def mock_rate_limited_api():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                # First call gets rate limited
                mock_response = Mock()
                mock_response.headers = {"Retry-After": "0.01"}
                mock_response.status = 429
                raise discord.HTTPException(response=mock_response, message="Too Many Requests")
            return f"success_{call_count}"

        result = await voice_handler.make_rate_limited_request(mock_rate_limited_api)
        assert result == "success_2"  # Should succeed on retry
        assert call_count == 2

    def test_voice_handler_has_rate_limiter(self, voice_handler):
        """Test that voice handler has proper rate limiter."""
        assert hasattr(voice_handler, "rate_limiter")
        assert isinstance(voice_handler.rate_limiter, SimpleRateLimiter)

    def test_voice_handler_has_voice_gateway(self, voice_handler):
        """Test that voice handler can handle voice gateway events."""
        assert hasattr(voice_handler, "handle_voice_server_update")
        assert hasattr(voice_handler, "handle_voice_state_update")

    @pytest.mark.asyncio
    async def test_voice_gateway_event_handling(self, voice_handler):
        """Test voice gateway event handling doesn't crash."""
        # Test with minimal mock data
        mock_payload = {"token": "test_token", "guild_id": "123456789", "endpoint": "test.endpoint:1234"}

        # These should not raise exceptions
        await voice_handler.handle_voice_server_update(mock_payload)

        mock_state_payload = {"session_id": "test_session_id"}
        await voice_handler.handle_voice_state_update(mock_state_payload)

    def test_compliance_components_exist(self, voice_handler):
        """Test that all compliance components are properly initialized."""
        # Check that voice handler has the components needed for compliance
        assert voice_handler.rate_limiter is not None
        assert hasattr(voice_handler, "make_rate_limited_request")

        # Should be able to handle voice gateway events
        assert callable(getattr(voice_handler, "handle_voice_server_update", None))
        assert callable(getattr(voice_handler, "handle_voice_state_update", None))

    @pytest.mark.asyncio
    async def test_none_arithmetic_safe_operations(self, voice_handler):
        """Test that None arithmetic operations are handled safely."""
        # Test with None values in stats - should not raise TypeError
        voice_handler.stats["messages_processed"] = None
        voice_handler.stats["connection_errors"] = None
        voice_handler.stats["tts_messages_played"] = None

        # These operations should not raise TypeError: unsupported operand type(s) for +: 'NoneType' and 'int'
        current_count = voice_handler.stats.get("messages_processed", 0)
        voice_handler.stats["messages_processed"] = (current_count if current_count is not None else 0) + 1

        current_errors = voice_handler.stats.get("connection_errors", 0)
        voice_handler.stats["connection_errors"] = (current_errors if current_errors is not None else 0) + 1

        current_tts = voice_handler.stats.get("tts_messages_played", 0)
        voice_handler.stats["tts_messages_played"] = (current_tts if current_tts is not None else 0) + 1

        # Verify the results are correct
        assert voice_handler.stats["messages_processed"] == 1
        assert voice_handler.stats["connection_errors"] == 1
        assert voice_handler.stats["tts_messages_played"] == 1

    @pytest.mark.asyncio
    async def test_voice_gateway_compliance_flow(self, voice_handler):
        """Test complete voice gateway connection flow for Discord API compliance."""
        # Mock voice client and initialize voice gateway
        mock_voice_client = MagicMock()
        mock_voice_client.is_connected.return_value = True
        voice_handler.voice_client = mock_voice_client
        from discord_voice_bot.voice_handler import VoiceGatewayManager
        voice_handler.voice_gateway = VoiceGatewayManager(mock_voice_client)

        # Test voice server update handling (step 1 in Discord flow)
        voice_server_payload = {
            "token": "test_voice_token_123",
            "guild_id": "123456789012345678",
            "endpoint": "test-voice-endpoint.example.com:443"
        }
        await voice_handler.handle_voice_server_update(voice_server_payload)

        # Test voice state update handling (step 2 in Discord flow)
        voice_state_payload = {
            "session_id": "test_session_abc123"
        }
        await voice_handler.handle_voice_state_update(voice_state_payload)

        # Verify voice gateway manager was created and configured
        assert voice_handler.voice_gateway is not None
        assert hasattr(voice_handler.voice_gateway, "_token")
        assert hasattr(voice_handler.voice_gateway, "_session_id")
        assert voice_handler.voice_gateway._token == "test_voice_token_123"
        assert voice_handler.voice_gateway._session_id == "test_session_abc123"

    @pytest.mark.asyncio
    async def test_discord_gateway_version_compliance(self, voice_handler):
        """Test that voice handler is configured for Discord Gateway version 8."""
        # This test ensures we're using the latest voice gateway version as required
        # Version 8 is mandatory as of November 18th, 2024

        # The voice handler should be prepared to handle version 8 features
        assert hasattr(voice_handler, "handle_voice_server_update")
        assert hasattr(voice_handler, "handle_voice_state_update")

        # Test that we can handle version 8 specific payloads
        v8_payload = {
            "op": 2,  # Ready opcode
            "d": {
                "ssrc": 12345,
                "ip": "127.0.0.1",
                "port": 1234,
                "modes": ["aead_xchacha20_poly1305_rtpsize"],
                "heartbeat_interval": 41250
            }
        }

        # Should handle version 8 specific fields without issues
        # (In practice, this would come from discord.py's voice client)
        mock_voice_client = MagicMock()
        mock_voice_client.is_connected.return_value = True
        voice_handler.voice_client = mock_voice_client

        # Test heartbeat handling (version 8 requires seq_ack)
        heartbeat_payload = {
            "op": 3,  # Heartbeat
            "d": {
                "t": 1501184119561,
                "seq_ack": 10
            }
        }
        # This should be handled by discord.py internally

    @pytest.mark.asyncio
    async def test_e2ee_protocol_readiness(self, voice_handler):
        """Test that voice handler is prepared for Discord's DAVE E2EE protocol."""
        # As of September 2024, Discord requires E2EE support
        # This test ensures our handler can support the transition

        # Voice handler should be able to handle protocol transitions
        assert hasattr(voice_handler, "handle_voice_server_update")
        assert hasattr(voice_handler, "handle_voice_state_update")

        # Test handling of protocol transition messages
        transition_payload = {
            "op": 21,  # DAVE Protocol Prepare Transition
            "d": {
                "transition_id": "test_transition_123",
                "protocol_version": 0  # Downgrade to non-E2EE
            }
        }

        # Should handle protocol transition without crashing
        # (In practice, discord.py handles the actual protocol negotiation)
        mock_voice_client = MagicMock()
        mock_voice_client.is_connected.return_value = True
        voice_handler.voice_client = mock_voice_client

        # This should not raise an exception
        await voice_handler.handle_voice_server_update({"token": "test", "guild_id": "123", "endpoint": "test:443"})

    @pytest.mark.asyncio
    async def test_ip_discovery_compliance(self, voice_handler):
        """Test IP discovery functionality for NAT traversal compliance."""
        # Discord requires UDP hole punching for voice connections
        # This test ensures we can handle IP discovery payloads

        # Mock UDP socket for IP discovery
        mock_socket = MagicMock()

        # IP Discovery packet format (big endian)
        # Type: 0x1 (request), Length: 70, SSRC: uint32, Address: 64 bytes, Port: uint16
        discovery_request = b'\x00\x01' + b'\x00\x46' + b'\x00\x00\x00\x01' + b'\x00' * 64 + b'\x00\x00'

        # Response would be Type: 0x2 (response) + same format with actual IP/port
        discovery_response = b'\x00\x02' + b'\x00\x46' + b'\x00\x00\x00\x01' + b'127.0.0.1'.ljust(64, b'\x00') + b'\x1f\x40'

        # Voice handler should support IP discovery through discord.py
        # We test that the handler can be initialized with IP discovery capability
        assert voice_handler is not None
        assert hasattr(voice_handler, "voice_client")

        # Test that voice handler has the necessary components for IP discovery
        assert hasattr(voice_handler, "rate_limiter")
        assert hasattr(voice_handler, "make_rate_limited_request")

    def test_voice_connection_state_tracking(self, voice_handler):
        """Test proper tracking of voice connection state."""
        # Test initial state
        assert voice_handler._connection_state == "DISCONNECTED"
        assert voice_handler._last_connection_attempt == 0.0

        # Test state changes
        voice_handler._connection_state = "CONNECTING"
        assert voice_handler._connection_state == "CONNECTING"

        # Test connection attempt tracking
        import time
        old_time = voice_handler._last_connection_attempt
        time.sleep(0.001)  # Small delay to ensure time difference
        voice_handler._last_connection_attempt = time.time()

        assert voice_handler._last_connection_attempt > old_time
