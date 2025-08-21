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
