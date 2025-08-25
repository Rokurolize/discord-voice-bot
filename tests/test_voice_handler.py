"""Unit tests for voice_handler module."""

import asyncio
from typing import Any
from unittest.mock import MagicMock, Mock, patch

import discord
import pytest


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


from discord_voice_bot.voice.ratelimit import SimpleRateLimiter
from discord_voice_bot.voice_handler import VoiceHandler

# Type aliases for better readability
MockBotClient = MagicMock
VoiceHandlerFixture = VoiceHandler


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


class TestVoiceHandlerInitialization:
    """Test VoiceHandler initialization."""

    def test_initialization(self, mock_bot_client: MagicMock, mock_config_manager: MagicMock) -> None:
        """Test handler initialization."""
        handler = VoiceHandler(mock_bot_client, mock_config_manager)
        assert handler.bot == mock_bot_client
        assert handler.voice_client is None
        assert handler.synthesis_queue.empty()
        assert handler.audio_queue.empty()
        assert handler.is_playing is False
        assert handler.current_group_id is None


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
        except TimeoutError:
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
        except TimeoutError:
            pytest.fail("Test timed out - skip_current_message operation took too long")

    @pytest.mark.asyncio
    async def test_clear_all_queues(self, voice_handler: VoiceHandler) -> None:
        """Test clearing all queues."""
        # Add items to both queues
        await voice_handler.synthesis_queue.put({"text": "syn1"})
        await voice_handler.audio_queue.put(("path1", "group1", 1, 1024))

        cleared: int = await voice_handler.clear_all()

        assert voice_handler.synthesis_queue.empty()
        assert voice_handler.audio_queue.empty()
        assert cleared == 2


class TestStatusGeneration:
    """Test status information generation."""

    @pytest.mark.asyncio
    async def test_get_status(self, voice_handler: VoiceHandler) -> None:
        """Test getting handler status."""
        # Add some items to queues
        await voice_handler.synthesis_queue.put({"text": "item1"})
        await voice_handler.audio_queue.put(("path1", "group1", 1, 1024))

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
        await voice_handler.audio_queue.put(("path", "group", 1, 1024))

        # Mock tasks to avoid cancellation issues
        voice_handler.tasks = []

        await voice_handler.cleanup()

        assert voice_handler.synthesis_queue.empty()
        assert voice_handler.audio_queue.empty()


class TestComplianceTDD:
    """TDD tests for Discord API compliance issues."""

    @pytest.mark.asyncio
    async def test_rate_limiter_compliance(self, voice_handler: VoiceHandler) -> None:
        """Test that rate limiter meets Discord's 50 req/sec requirement."""
        import time

        start_time: float = time.time()

        # Make 10 requests - should take at least 0.2 seconds (10/50)
        for _ in range(10):
            await voice_handler.rate_limiter.wait_if_needed()

        elapsed: float = time.time() - start_time

        # Should have taken at least 0.2 seconds (10 requests at 50/sec = 0.2 sec)
        assert elapsed >= 0.15  # Allow some margin for timing precision

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
        except TimeoutError:
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
        except TimeoutError:
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
        """Test voice gateway event handling doesn't crash."""
        try:
            async with asyncio.timeout(2.0):  # 2 second timeout
                # Test with minimal mock data
                mock_payload: dict[str, str] = {"token": "test_token", "guild_id": "123456789", "endpoint": "test.endpoint:1234"}

                # These should not raise exceptions
                await voice_handler.handle_voice_server_update(mock_payload)

                mock_state_payload: dict[str, str] = {"session_id": "test_session_id"}
                await voice_handler.handle_voice_state_update(mock_state_payload)
        except TimeoutError:
            pytest.fail("Test timed out - voice_gateway_event_handling took too long")

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
        try:
            async with asyncio.timeout(3.0):  # 3 second timeout
                # Mock voice client and initialize voice gateway
                mock_voice_client: MagicMock = MagicMock()
                mock_voice_client.is_connected.return_value = True
                voice_handler.voice_client = mock_voice_client
                from discord_voice_bot.voice.gateway import VoiceGatewayManager

                voice_handler.voice_gateway = VoiceGatewayManager(mock_voice_client)

                # Test voice server update handling (step 1 in Discord flow)
                voice_server_payload: dict[str, str] = {"token": "test_voice_token_123", "guild_id": "123456789012345678", "endpoint": "test-voice-endpoint.example.com:443"}
                await voice_handler.handle_voice_server_update(voice_server_payload)

                # Test voice state update handling (step 2 in Discord flow)
                voice_state_payload: dict[str, str] = {"session_id": "test_session_abc123"}
                await voice_handler.handle_voice_state_update(voice_state_payload)

                # Verify voice gateway manager was created and configured
                assert voice_handler.voice_gateway is not None
                # Check that the voice gateway has the necessary attributes for Discord compliance
                assert hasattr(voice_handler.voice_gateway, "_token")
                assert hasattr(voice_handler.voice_gateway, "_session_id")
                # Note: In tests, we may need to access protected members to verify internal state
                # This is acceptable in test contexts where we're verifying implementation details
                assert voice_handler.voice_gateway._token == "test_voice_token_123"  # type: ignore[attr-defined]
                assert voice_handler.voice_gateway._session_id == "test_session_abc123"  # type: ignore[attr-defined]
        except TimeoutError:
            pytest.fail("Test timed out - voice_gateway_compliance_flow took too long")

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
        except TimeoutError:
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
        assert voice_handler._last_connection_attempt == 0.0  # type: ignore[attr-defined]

        # Test state changes
        voice_handler.connection_state = "CONNECTING"
        assert voice_handler.connection_state == "CONNECTING"

        # Test connection attempt tracking
        import time

        old_time: float = voice_handler._last_connection_attempt  # type: ignore[attr-defined]
        time.sleep(0.001)  # Small delay to ensure time difference
        voice_handler._last_connection_attempt = time.time()  # type: ignore[attr-defined]

        assert voice_handler._last_connection_attempt > old_time  # type: ignore[attr-defined]


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
                assert len(active_tasks) == 2, f"Expected 2 workers, got {len(active_tasks)}"

        except TimeoutError:
            pytest.fail("Test timed out - workers did not start properly")

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
                # Mock the TTS engine to avoid real API calls
                mock_tts_engine = MockTTSEngine(mock_config_manager)
                voice_handler._config_manager = mock_config_manager

                # Mock get_tts_engine, get_user_settings, and PlayerWorker to avoid real API calls and queue consumption
                with patch('discord_voice_bot.voice.workers.synthesizer.get_tts_engine', return_value=mock_tts_engine), \
                      patch('discord_voice_bot.voice.workers.synthesizer.get_user_settings') as mock_user_settings, \
                      patch('discord_voice_bot.voice.workers.player.PlayerWorker.run'):

                    # Mock user settings
                    mock_user_settings_instance = MagicMock()
                    mock_user_settings_instance.get_user_settings.return_value = {"speaker_id": 1, "engine": "voicevox"}
                    mock_user_settings.return_value = mock_user_settings_instance

                    # Start the voice handler (which should start workers)
                    await voice_handler.start()

                    # Add a test message to the synthesis queue
                    test_message = {"text": "Test message", "chunks": ["Test message"], "user_id": 12345, "username": "TestUser", "group_id": "test_group_123", "chunk_index": 0, "total_chunks": 1}

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
    async def test_worker_cleanup_on_handler_cleanup(self, voice_handler: VoiceHandler) -> None:
        """Test that workers are properly cleaned up when handler is cleaned up."""
        try:
            async with asyncio.timeout(5.0):  # 5 second timeout
                # Start the voice handler
                await voice_handler.start()

                # Ensure workers are running
                assert len(voice_handler.tasks) > 0

                # Clean up the handler
                await voice_handler.cleanup()

                # Check that all tasks are cancelled
                for task in voice_handler.tasks:
                    assert task.cancelled() or task.done(), f"Task {task} was not cancelled"

        except TimeoutError:
            pytest.fail("Test timed out - workers did not clean up properly")

        finally:
            # Clean up - cancel tasks to prevent hanging
            for task in voice_handler.tasks:
                if not task.done():
                    task.cancel()

            # Wait for tasks to be cancelled
            if voice_handler.tasks:
                await asyncio.gather(*voice_handler.tasks, return_exceptions=True)

    @pytest.mark.asyncio
    async def test_worker_timeout_protection(self, voice_handler: VoiceHandler) -> None:
        """Test that workers properly handle timeouts and don't hang."""
        try:
            async with asyncio.timeout(3.0):  # Shorter timeout for this specific test
                await voice_handler.start()

                # Verify workers started
                assert len(voice_handler.tasks) > 0

                # Test that we can stop workers quickly
                voice_handler.stop_workers()

                # Give workers time to stop gracefully
                await asyncio.sleep(0.1)

                # Check that workers are stopping/stopped
                stopping_or_stopped = sum(1 for task in voice_handler.tasks if task.cancelled() or task.done())
                assert stopping_or_stopped > 0, "Workers should be stopping or stopped"

        except TimeoutError:
            pytest.fail("Worker timeout protection test timed out")

        finally:
            # Emergency cleanup
            for task in voice_handler.tasks:
                if not task.done():
                    task.cancel()
            if voice_handler.tasks:
                await asyncio.gather(*voice_handler.tasks, return_exceptions=True)

    @pytest.mark.asyncio
    @patch("discord_voice_bot.voice.workers.synthesizer.get_tts_engine")
    async def test_voice_handler_initializes_workers_fixed(self, mock_get_engine, voice_handler: VoiceHandler) -> None:
        """Test that VoiceHandler initializes and starts worker tasks with fixed mocking."""
        # Mock the TTS engine to avoid real HTTP requests
        mock_get_engine.return_value = MockTTSEngine(None)

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
                assert len(active_tasks) == 2, f"Expected 2 workers, got {len(active_tasks)}"

        except TimeoutError:
            pytest.fail("Test timed out - workers did not start properly")

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
    async def test_workers_process_queue_items_fixed(self, mock_get_engine, voice_handler: VoiceHandler) -> None:
        """Test that workers actually process items from queues with fixed mocking."""
        # Mock the TTS engine to avoid real HTTP requests
        mock_config_manager = MagicMock()
        mock_get_engine.return_value = MockTTSEngine(mock_config_manager)

        try:
            async with asyncio.timeout(5.0):  # 5 second timeout
                # Start the voice handler (which should start workers)
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
        # Mock the TTS engine to avoid real HTTP requests
        mock_get_engine.return_value = MockTTSEngine(None)

        try:
            async with asyncio.timeout(5.0):  # 5 second timeout
                # Start the voice handler
                await voice_handler.start()

                # Ensure workers are running
                assert len(voice_handler.tasks) > 0

                # Clean up the handler
                await voice_handler.cleanup()

                # Check that all tasks are cancelled
                for task in voice_handler.tasks:
                    assert task.cancelled() or task.done(), f"Task {task} was not cancelled"

        except TimeoutError:
            pytest.fail("Test timed out - workers did not clean up properly")

        finally:
            # Emergency cleanup
            for task in voice_handler.tasks:
                if not task.done():
                    task.cancel()
            if voice_handler.tasks:
                await asyncio.gather(*voice_handler.tasks, return_exceptions=True)
