"""Unit tests for tts_engine module."""

from unittest.mock import AsyncMock, patch

import pytest

from discord_voice_bot.config import Config
from discord_voice_bot.tts_engine import TTSEngine


@pytest.fixture
async def tts_engine_with_mocks(config: Config):
    """
    Fixture to provide a TTSEngine instance with mocked dependencies.
    This isolates the TTSEngine logic from the actual API calls.
    """
    with patch("discord_voice_bot.tts_engine.TTSEngine._generate_audio_query", new_callable=AsyncMock) as mock_gen_query, \
         patch("discord_voice_bot.tts_engine.TTSEngine._synthesize_from_query", new_callable=AsyncMock) as mock_synth_query, \
         patch("discord_voice_bot.tts_engine.TTSHealthMonitor.perform_health_check", new_callable=AsyncMock) as mock_health_check, \
         patch("discord_voice_bot.tts_engine.TTSClient.close_session", new_callable=AsyncMock) as mock_close_session:

        mock_gen_query.return_value = {"mora": "data"}
        mock_synth_query.return_value = b"mocked_audio_data"
        mock_health_check.return_value = True

        engine = TTSEngine(config)
        await engine.start()

        yield engine, mock_gen_query, mock_synth_query, mock_health_check, mock_close_session

        await engine.close()


@pytest.mark.asyncio
class TestHealthCheck:
    """Test health check functionality."""

    async def test_health_check_healthy(self, tts_engine_with_mocks):
        """Test health check when the configured engine is healthy."""
        engine, _, _, mock_health_check, _ = tts_engine_with_mocks
        mock_health_check.return_value = True

        result = await engine.health_check()

        assert result is True
        mock_health_check.assert_called_once()

    async def test_health_check_unhealthy(self, tts_engine_with_mocks):
        """Test health check when the configured engine is unhealthy."""
        engine, _, _, mock_health_check, _ = tts_engine_with_mocks
        mock_health_check.return_value = False

        result = await engine.health_check()

        assert result is False
        mock_health_check.assert_called_once()


@pytest.mark.asyncio
class TestSynthesizeAudio:
    """Test audio synthesis."""

    async def test_synthesize_audio_with_empty_text(self, tts_engine_with_mocks):
        """Empty text should return None and not call the client."""
        engine, mock_gen_query, mock_synth_query, _, _ = tts_engine_with_mocks

        result = await engine.synthesize_audio("")

        assert result is None
        mock_gen_query.assert_not_called()
        mock_synth_query.assert_not_called()

    async def test_synthesize_with_default_engine(self, tts_engine_with_mocks, config: Config):
        """Should synthesize using the engine specified in the config."""
        engine, mock_gen_query, mock_synth_query, _, _ = tts_engine_with_mocks

        result = await engine.synthesize_audio("test")

        assert result == b"mocked_audio_data"
        mock_gen_query.assert_called_once_with("test", None, None)
        mock_synth_query.assert_called_once()

    async def test_synthesize_with_overridden_engine(self, tts_engine_with_mocks):
        """Should synthesize using the engine passed as an argument."""
        engine, mock_gen_query, mock_synth_query, _, _ = tts_engine_with_mocks

        result = await engine.synthesize_audio("test", engine_name="aivis")

        assert result == b"mocked_audio_data"
        mock_gen_query.assert_called_once_with("test", None, "aivis")
        mock_synth_query.assert_called_once()

@pytest.mark.asyncio
class TestEngineLifecycle:
    """Test engine lifecycle methods."""

    async def test_close_closes_all_clients(self, tts_engine_with_mocks):
        """Calling close on the main engine should close all underlying clients."""
        engine, _, _, _, mock_close_session = tts_engine_with_mocks

        # The fixture automatically calls close, so we just need to assert it was called.
        # To be more explicit, we can call it again.
        await engine.close()

        # The mock was created on the TTSClient class, so it should be called.
        mock_close_session.assert_awaited()
        # Verify idempotency
        assert mock_close_session.await_count >= 1
