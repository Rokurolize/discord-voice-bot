"""Unit tests for voice_handler module."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.voice_handler import VoiceHandler


@pytest.fixture
def voice_handler(mock_voice_client):
    """Create a VoiceHandler instance with mocked voice client."""
    handler = VoiceHandler(mock_voice_client)
    return handler


class TestVoiceHandlerInitialization:
    """Test VoiceHandler initialization."""

    def test_initialization(self, mock_voice_client):
        """Test handler initialization."""
        handler = VoiceHandler(mock_voice_client)
        assert handler.voice_client == mock_voice_client
        assert handler.synthesis_queue.empty()
        assert handler.audio_queue.empty()
        assert handler.is_playing is False
        assert handler.current_group_id is None


class TestQueueManagement:
    """Test queue management functionality."""

    @pytest.mark.asyncio
    async def test_add_to_synthesis_queue(self, voice_handler):
        """Test adding items to synthesis queue."""
        item = {"text": "Hello", "group_id": "group1", "chunk_index": 0, "total_chunks": 1}

        await voice_handler.add_to_queue(item)

        assert not voice_handler.synthesis_queue.empty()
        queued_item = await voice_handler.synthesis_queue.get()
        assert queued_item == item

    @pytest.mark.asyncio
    async def test_skip_current_message(self, voice_handler):
        """Test skipping current message group."""
        # Add items with same group
        for i in range(3):
            await voice_handler.synthesis_queue.put({"text": f"Text {i}", "group_id": "group1"})

        # Add items with different group
        await voice_handler.synthesis_queue.put({"text": "Different", "group_id": "group2"})

        voice_handler.current_group_id = "group1"
        await voice_handler.skip_current()

        # Should only have group2 item left
        assert voice_handler.synthesis_queue.qsize() == 1
        item = await voice_handler.synthesis_queue.get()
        assert item["group_id"] == "group2"

    @pytest.mark.asyncio
    async def test_clear_all_queues(self, voice_handler):
        """Test clearing all queues."""
        # Add items to both queues
        await voice_handler.synthesis_queue.put({"text": "syn1"})
        await voice_handler.audio_queue.put(("path1", "group1"))

        await voice_handler.clear_all()

        assert voice_handler.synthesis_queue.empty()
        assert voice_handler.audio_queue.empty()


class TestAudioPlayback:
    """Test audio playback functionality."""

    @pytest.mark.asyncio
    async def test_play_audio_success(self, voice_handler):
        """Test successful audio playback."""
        audio_path = "/tmp/test.wav"

        with patch("discord.FFmpegPCMAudio") as mock_ffmpeg:
            mock_audio = MagicMock()
            mock_ffmpeg.return_value = mock_audio

            # Simulate playback
            voice_handler.voice_client.is_playing.return_value = False

            await voice_handler._play_audio(audio_path, "group1")

            voice_handler.voice_client.play.assert_called_once()
            assert voice_handler.current_group_id == "group1"

    @pytest.mark.asyncio
    async def test_play_audio_while_playing(self, voice_handler):
        """Test audio queuing when already playing."""
        voice_handler.voice_client.is_playing.return_value = True
        voice_handler.is_playing = True

        # Should not play immediately
        audio_path = "/tmp/test.wav"
        await voice_handler._play_audio(audio_path, "group1")

        # Should be queued instead
        assert voice_handler.audio_queue.qsize() == 1

    def test_playback_complete_callback(self, voice_handler):
        """Test playback completion callback."""
        voice_handler.is_playing = True
        voice_handler.current_group_id = "group1"

        # Call the after callback
        voice_handler._playback_complete(None)

        assert voice_handler.is_playing is False
        assert voice_handler.current_group_id is None


class TestSynthesisTask:
    """Test synthesis task functionality."""

    @pytest.mark.asyncio
    async def test_synthesis_task_processes_queue(self, voice_handler):
        """Test synthesis task processes items from queue."""
        with patch("src.voice_handler.tts_engine") as mock_engine:
            mock_engine.synthesize = AsyncMock(return_value="/tmp/audio.wav")

            # Add item to queue
            await voice_handler.synthesis_queue.put({"text": "Hello", "group_id": "group1"})

            # Run synthesis task briefly
            task = asyncio.create_task(voice_handler._synthesis_task())
            await asyncio.sleep(0.1)
            task.cancel()

            try:
                await task
            except asyncio.CancelledError:
                pass

            # Should have called synthesize
            mock_engine.synthesize.assert_called_once()


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
        assert status["is_playing"] is True
        assert status["messages_played"] == 10
        assert status["messages_skipped"] == 2


class TestCleanup:
    """Test cleanup functionality."""

    @pytest.mark.asyncio
    async def test_cleanup_cancels_tasks(self, voice_handler):
        """Test cleanup cancels running tasks."""
        # Create mock tasks
        mock_task1 = AsyncMock()
        mock_task2 = AsyncMock()
        voice_handler.tasks = [mock_task1, mock_task2]

        await voice_handler.cleanup()

        mock_task1.cancel.assert_called_once()
        mock_task2.cancel.assert_called_once()

    @pytest.mark.asyncio
    async def test_cleanup_clears_queues(self, voice_handler):
        """Test cleanup clears all queues."""
        await voice_handler.synthesis_queue.put({"text": "item"})
        await voice_handler.audio_queue.put(("path", "group"))

        await voice_handler.cleanup()

        assert voice_handler.synthesis_queue.empty()
        assert voice_handler.audio_queue.empty()
