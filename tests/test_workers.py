"""Unit tests for voice workers."""

import asyncio
from typing import Any
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import discord
import pytest

from discord_voice_bot.voice_handler import VoiceHandler


class MockTTSEngine:
    """Mock TTS engine that doesn't make real HTTP requests."""

    def __init__(self, config_manager):
        self._config_manager = config_manager

    async def synthesize_audio(self, text: str, speaker_id: int | None = None, engine_name: str | None = None) -> bytes | None:
        """Mock audio synthesis that returns fake WAV data."""
        if not text or not text.strip():
            return None

        # Create a proper WAV file header with minimal audio data
        # WAV header structure:
        # RIFF header (12 bytes)
        # fmt chunk (24 bytes)
        # data chunk header (8 bytes) + data

        # Calculate sizes
        fmt_chunk_size = 16  # PCM format
        sample_rate = 22050
        channels = 1
        bits_per_sample = 16
        bytes_per_sample = bits_per_sample // 8
        block_align = channels * bytes_per_sample
        byte_rate = sample_rate * block_align

        # Create some minimal audio data (silence)
        audio_samples = 480  # 0.02 seconds at 24kHz
        audio_data_size = audio_samples * bytes_per_sample
        audio_data = b"\x00" * audio_data_size  # Silence

        # Total file size
        file_size = 36 + audio_data_size  # 12 (RIFF) + 24 (fmt) + 8 (data header) + data

        # Build WAV header
        header = b"RIFF"
        header += file_size.to_bytes(4, "little")
        header += b"WAVE"

        # fmt chunk
        header += b"fmt "
        header += fmt_chunk_size.to_bytes(4, "little")
        header += (1).to_bytes(2, "little")  # PCM format
        header += channels.to_bytes(2, "little")
        header += sample_rate.to_bytes(4, "little")
        header += byte_rate.to_bytes(4, "little")
        header += block_align.to_bytes(2, "little")
        header += bits_per_sample.to_bytes(2, "little")

        # data chunk
        header += b"data"
        header += audio_data_size.to_bytes(4, "little")

        return header + audio_data

    async def create_audio_source(self, text: str, speaker_id: int | None = None, engine_name: str | None = None):
        """Mock audio source creation."""
        return

    def cleanup_audio_source(self, audio_source):
        """Mock cleanup."""


@pytest.fixture
def mock_bot_client() -> MagicMock:
    """Create a mock bot client."""
    bot = MagicMock()
    bot.get_channel = MagicMock()
    return bot


@pytest.fixture
def mock_config_manager() -> MagicMock:
    """Create a mock config manager."""
    config_manager = MagicMock()
    # Mock the required configuration methods
    config_manager.get_tts_engine.return_value = "voicevox"
    config_manager.get_engines.return_value = {
        "voicevox": {"url": "http://localhost:50021", "default_speaker": 1}
    }
    config_manager.get_audio_sample_rate.return_value = 24000
    config_manager.get_audio_channels.return_value = 1
    config_manager.get_log_level.return_value = "INFO"
    config_manager.get_discord_token.return_value = "test_token"
    config_manager.get_target_guild_id.return_value = 123456789
    config_manager.get_target_voice_channel_id.return_value = 987654321
    config_manager.get_command_prefix.return_value = "!tts"
    config_manager.get_engine_config.return_value = {"speakers": {"test": 1}}
    config_manager.get_engines.return_value = {
        "voicevox": {"url": "http://localhost:50021", "default_speaker": 1}
    }
    config_manager.get_max_message_length.return_value = 200
    config_manager.get_message_queue_size.return_value = 10
    config_manager.get_reconnect_delay.return_value = 5
    config_manager.get_rate_limit_messages.return_value = 5
    config_manager.get_rate_limit_period.return_value = 60
    config_manager.get_log_file.return_value = None
    config_manager.is_debug.return_value = False
    config_manager.get_enable_self_message_processing.return_value = False
    return config_manager


@pytest.fixture
def voice_handler(mock_bot_client: MagicMock, mock_config_manager: MagicMock) -> VoiceHandler:
    """Create a VoiceHandler instance with mocked bot client."""
    handler = VoiceHandler(mock_bot_client, mock_config_manager)
    return handler


class TestWorkerInitialization:
    """Test Worker initialization and startup."""

    @pytest.mark.asyncio
    async def test_voice_handler_initializes_workers(self, voice_handler: VoiceHandler) -> None:
        """Test that VoiceHandler initializes and starts worker tasks."""
        # Use a timeout to prevent hanging
        try:
            async with asyncio.timeout(5.0):  # 5 second timeout
                # Start the voice handler
                await voice_handler.start()

                # Check that worker tasks are created and running
                assert len(voice_handler.tasks) > 0, "No worker tasks were created"

                # Check that tasks are not done (still running)
                active_tasks = [task for task in voice_handler.tasks if not task.done()]
                assert len(active_tasks) > 0, "Worker tasks finished immediately"

                # Check that we have the expected number of workers
                # (SynthesizerWorker + PlayerWorker)
                assert len(active_tasks) >= 2, f"Expected at least 2 workers, got {len(active_tasks)}"

        except TimeoutError:
            pytest.fail("Test timed out - voice_handler_initializes_workers took too long")

        finally:
            # Clean up - stop workers gracefully and cancel tasks
            voice_handler.stop_workers()

            for task in voice_handler.tasks:
                if not task.done():
                    task.cancel()

            # Wait for tasks to be cancelled
            if voice_handler.tasks:
                await asyncio.gather(*voice_handler.tasks, return_exceptions=True)

    @pytest.mark.asyncio
    async def test_workers_process_queue_items(self, voice_handler: VoiceHandler, mock_config_manager: MagicMock) -> None:
        """Test that workers actually process items from queues."""
        try:
            async with asyncio.timeout(5.0):  # 5 second timeout
                with patch('discord_voice_bot.voice.workers.synthesizer.get_tts_engine') as mock_get_engine:
                    mock_get_engine.return_value = MockTTSEngine(mock_config_manager)

                    # Start the voice handler
                    await voice_handler.start()

                    # Add a test message to the synthesis queue
                    test_message = {"text": "Test message", "chunks": ["Test message"], "user_id": 12345, "username": "TestUser", "group_id": "test_group_123"}

                    await voice_handler.add_to_queue(test_message)

                    # Wait a short time for processing
                    await asyncio.sleep(0.1)

                    # Check that synthesis queue is empty (processed)
                    assert voice_handler.synthesis_queue.empty(), "Message was not processed from synthesis queue"

                    # Check that audio queue has an item (processed by SynthesizerWorker)
                    assert not voice_handler.audio_queue.empty(), "Audio was not queued after synthesis"

        except TimeoutError:
            pytest.fail("Test timed out - workers_process_queue_items took too long")

        finally:
            # Clean up - stop workers gracefully and cancel tasks
            voice_handler.stop_workers()

            for task in voice_handler.tasks:
                if not task.done():
                    task.cancel()

            # Wait for tasks to be cancelled
            if voice_handler.tasks:
                await asyncio.gather(*voice_handler.tasks, return_exceptions=True)

    @pytest.mark.asyncio
    async def test_worker_cleanup_on_handler_cleanup(self, voice_handler: VoiceHandler) -> None:
        """Test that workers are properly cleaned up when handler is cleaned up."""
        try:
            async with asyncio.timeout(5.0):  # 5 second timeout
                # Start the voice handler
                await voice_handler.start()

                # Verify workers are running
                assert len(voice_handler.tasks) > 0, "No worker tasks were created"

                # Mock tasks to avoid cancellation issues
                voice_handler.tasks = []

                await voice_handler.cleanup()

                # Workers should be stopped
                assert voice_handler._synthesizer_worker is None or voice_handler._synthesizer_worker._running == False
                assert voice_handler._player_worker is None or voice_handler._player_worker._running == False

        except TimeoutError:
            pytest.fail("Test timed out - worker_cleanup_on_handler_cleanup took too long")

    @pytest.mark.asyncio
    async def test_worker_timeout_protection(self, voice_handler: VoiceHandler) -> None:
        """Test that workers properly handle timeouts and don't hang."""
        try:
            async with asyncio.timeout(3.0):  # Shorter timeout for this specific test
                # Start the voice handler
                await voice_handler.start()

                # Add a message that might cause timeout
                test_message = {"text": "Test", "chunks": ["Test"], "user_id": 12345, "username": "TestUser", "group_id": "test_group"}

                await voice_handler.add_to_queue(test_message)

                # The test should complete without hanging, even if TTS synthesis times out
                await asyncio.sleep(0.5)

        except TimeoutError:
            pytest.fail("Test timed out - worker_timeout_protection took too long")

        finally:
            # Clean up - stop workers gracefully and cancel tasks
            voice_handler.stop_workers()

            for task in voice_handler.tasks:
                if not task.done():
                    task.cancel()

            # Wait for tasks to be cancelled
            if voice_handler.tasks:
                await asyncio.gather(*voice_handler.tasks, return_exceptions=True)

    @pytest.mark.asyncio
    @patch("discord_voice_bot.voice.workers.synthesizer.get_tts_engine")
    async def test_voice_handler_initializes_workers_fixed(self, mock_get_engine, voice_handler: VoiceHandler) -> None:
        """Test that VoiceHandler initializes and starts worker tasks with fixed mocking."""
        try:
            async with asyncio.timeout(5.0):  # 5 second timeout
                # Mock the TTS engine to avoid real HTTP requests
                mock_config_manager = MagicMock()
                mock_get_engine.return_value = MockTTSEngine(mock_config_manager)

                # Start the voice handler
                await voice_handler.start()

                # Check that worker tasks are created and running
                assert len(voice_handler.tasks) > 0, "No worker tasks were created"

                # Check that tasks are not done (still running)
                active_tasks = [task for task in voice_handler.tasks if not task.done()]
                assert len(active_tasks) > 0, "Worker tasks finished immediately"

        except TimeoutError:
            pytest.fail("Test timed out - voice_handler_initializes_workers_fixed took too long")

        finally:
            # Clean up - stop workers gracefully and cancel tasks
            voice_handler.stop_workers()

            for task in voice_handler.tasks:
                if not task.done():
                    task.cancel()

            # Wait for tasks to be cancelled
            if voice_handler.tasks:
                await asyncio.gather(*voice_handler.tasks, return_exceptions=True)

    @pytest.mark.asyncio
    @patch("discord_voice_bot.voice.workers.synthesizer.get_tts_engine")
    @patch("discord_voice_bot.voice.workers.player.PlayerWorker")
    async def test_workers_process_queue_items_fixed(self, mock_player_worker, mock_get_engine, voice_handler: VoiceHandler) -> None:
        """Test that workers actually process items from queues with fixed mocking."""
        # Mock the TTS engine to avoid real HTTP requests
        mock_config_manager = MagicMock()
        mock_get_engine.return_value = MockTTSEngine(mock_config_manager)

        # Mock PlayerWorker to prevent it from consuming the audio queue
        mock_player_worker_instance = MagicMock()
        mock_player_worker.return_value = mock_player_worker_instance
        mock_player_worker_instance.run = AsyncMock()
        mock_player_worker_instance.stop = MagicMock()

        try:
            async with asyncio.timeout(5.0):  # 5 second timeout
                # Start the voice handler (which should start workers)
                await voice_handler.start(start_player=False)

                # Add a test message to the synthesis queue
                test_message = {"text": "Test message", "chunks": ["Test message"], "user_id": 12345, "username": "TestUser", "group_id": "test_group_123"}

                await voice_handler.add_to_queue(test_message)

                # Wait a short time for processing
                await asyncio.sleep(0.1)

                # Check that synthesis queue is empty (processed)
                assert voice_handler.synthesis_queue.empty(), "Message was not processed from synthesis queue"

                # Check that audio queue has an item (processed by SynthesizerWorker)
                assert not voice_handler.audio_queue.empty(), "Audio was not queued after synthesis"

        except TimeoutError:
            pytest.fail("Test timed out - workers did not process queue items")

        finally:
            # Clean up - stop workers gracefully and cancel tasks
            voice_handler.stop_workers()

            for task in voice_handler.tasks:
                if not task.done():
                    task.cancel()

            # Wait for tasks to be cancelled
            if voice_handler.tasks:
                await asyncio.gather(*voice_handler.tasks, return_exceptions=True)

    @pytest.mark.asyncio
    @patch("discord_voice_bot.voice.workers.synthesizer.get_tts_engine")
    async def test_worker_cleanup_on_handler_cleanup_fixed(self, mock_get_engine, voice_handler: VoiceHandler) -> None:
        """Test that workers are properly cleaned up when handler is cleaned up with fixed mocking."""
        try:
            async with asyncio.timeout(5.0):  # 5 second timeout
                # Mock the TTS engine to avoid real HTTP requests
                mock_config_manager = MagicMock()
                mock_get_engine.return_value = MockTTSEngine(mock_config_manager)

                # Start the voice handler
                await voice_handler.start()

                # Verify workers are running
                assert len(voice_handler.tasks) > 0, "No worker tasks were created"

                # Mock tasks to avoid cancellation issues
                voice_handler.tasks = []

                await voice_handler.cleanup()

                # Workers should be stopped
                assert voice_handler._synthesizer_worker is None or voice_handler._synthesizer_worker._running == False
                assert voice_handler._player_worker is None or voice_handler._player_worker._running == False

        except TimeoutError:
            pytest.fail("Test timed out - worker_cleanup_on_handler_cleanup_fixed took too long")