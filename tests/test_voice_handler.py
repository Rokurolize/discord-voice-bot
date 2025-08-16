"""Unit tests for voice_handler module."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from src.voice_handler import VoiceHandler


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
        message_data = {
            "text": "Hello",
            "chunks": ["Hello"],
            "user_id": 123,
            "username": "TestUser",
            "group_id": "test_group"
        }
        
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
            await voice_handler.synthesis_queue.put({
                "text": f"Text {i}",
                "group_id": "group1"
            })
        
        # Add items with different group
        await voice_handler.synthesis_queue.put({
            "text": "Different",
            "group_id": "group2"
        })
        
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