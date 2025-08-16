"""Unit tests for tts_engine module using mocks."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.tts_engine import TTSEngine


@pytest.fixture
def tts_engine():
    """Create a TTSEngine instance with mocked session."""
    with patch("src.tts_engine.aiohttp.ClientSession") as mock_session:
        engine = TTSEngine()
        engine.session = mock_session
        yield engine


@pytest.fixture
def mock_response():
    """Create a mock aiohttp response."""
    response = AsyncMock()
    response.status = 200
    response.json = AsyncMock(return_value={})
    response.read = AsyncMock(return_value=b"mock_audio_data")
    return response


class TestTTSEngineInitialization:
    """Test TTSEngine initialization."""

    def test_default_initialization(self):
        """Test default engine initialization."""
        with patch("src.tts_engine.aiohttp.ClientSession"):
            engine = TTSEngine()
            assert engine.engine_type == "aivis"
            assert engine.speaker_id == 1512153250
            assert engine.api_url == "http://127.0.0.1:10101"

    def test_voicevox_initialization(self):
        """Test VOICEVOX engine initialization."""
        with patch.dict("os.environ", {"TTS_ENGINE": "voicevox", "TTS_SPEAKER": "sexy"}):
            with patch("src.tts_engine.aiohttp.ClientSession"):
                engine = TTSEngine()
                assert engine.engine_type == "voicevox"
                assert engine.speaker_id == 5
                assert engine.api_url == "http://localhost:50021"

    def test_custom_api_url(self):
        """Test custom API URL from environment."""
        with patch.dict("os.environ", {"TTS_API_URL": "http://custom:8080"}):
            with patch("src.tts_engine.aiohttp.ClientSession"):
                engine = TTSEngine()
                assert engine.api_url == "http://custom:8080"


class TestHealthCheck:
    """Test health check functionality."""

    @pytest.mark.asyncio
    async def test_health_check_success(self, tts_engine, mock_response):
        """Health check should succeed with valid response."""
        mock_response.json.return_value = {"version": "1.0.0"}
        tts_engine.session.get.return_value.__aenter__.return_value = mock_response

        result = await tts_engine.health_check()
        assert result is True

    @pytest.mark.asyncio
    async def test_health_check_failure(self, tts_engine):
        """Health check should fail on connection error."""
        tts_engine.session.get.side_effect = Exception("Connection failed")

        result = await tts_engine.health_check()
        assert result is False

    @pytest.mark.asyncio
    async def test_health_check_invalid_status(self, tts_engine, mock_response):
        """Health check should fail on non-200 status."""
        mock_response.status = 500
        tts_engine.session.get.return_value.__aenter__.return_value = mock_response

        result = await tts_engine.health_check()
        assert result is False


class TestSynthesizeVoiceVox:
    """Test VOICEVOX synthesis."""

    @pytest.mark.asyncio
    async def test_synthesize_voicevox_success(self, tts_engine, mock_response):
        """VOICEVOX synthesis should return audio path."""
        tts_engine.engine_type = "voicevox"
        tts_engine.api_url = "http://localhost:50021"
        tts_engine.speaker_id = 3

        # Mock query response
        query_response = AsyncMock()
        query_response.status = 200
        query_response.json = AsyncMock(return_value={"speedScale": 1.0})

        # Mock synthesis response
        synth_response = AsyncMock()
        synth_response.status = 200
        synth_response.read = AsyncMock(return_value=b"audio_data")

        tts_engine.session.post.return_value.__aenter__.side_effect = [query_response, synth_response]

        with patch("builtins.open"):
            with patch("tempfile.NamedTemporaryFile") as mock_temp:
                mock_file = MagicMock()
                mock_file.name = "/tmp/test_audio.wav"
                mock_temp.return_value.__enter__.return_value = mock_file

                result = await tts_engine._synthesize_voicevox("Hello")

                assert result == "/tmp/test_audio.wav"
                assert tts_engine.session.post.call_count == 2

    @pytest.mark.asyncio
    async def test_synthesize_voicevox_query_failure(self, tts_engine, mock_response):
        """VOICEVOX synthesis should handle query failure."""
        tts_engine.engine_type = "voicevox"
        mock_response.status = 500
        tts_engine.session.post.return_value.__aenter__.return_value = mock_response

        result = await tts_engine._synthesize_voicevox("Hello")
        assert result is None


class TestSynthesizeAivis:
    """Test AivisSpeech synthesis."""

    @pytest.mark.asyncio
    async def test_synthesize_aivis_success(self, tts_engine, mock_response):
        """AivisSpeech synthesis should return audio path."""
        tts_engine.engine_type = "aivis"
        tts_engine.api_url = "http://127.0.0.1:10101"
        tts_engine.speaker_id = 1512153250

        mock_response.status = 200
        mock_response.read = AsyncMock(return_value=b"audio_data")
        tts_engine.session.post.return_value.__aenter__.return_value = mock_response

        with patch("builtins.open"):
            with patch("tempfile.NamedTemporaryFile") as mock_temp:
                mock_file = MagicMock()
                mock_file.name = "/tmp/test_audio.wav"
                mock_temp.return_value.__enter__.return_value = mock_file

                result = await tts_engine._synthesize_aivis("Hello")

                assert result == "/tmp/test_audio.wav"
                assert tts_engine.session.post.call_count == 1

    @pytest.mark.asyncio
    async def test_synthesize_aivis_failure(self, tts_engine, mock_response):
        """AivisSpeech synthesis should handle API failure."""
        tts_engine.engine_type = "aivis"
        mock_response.status = 500
        tts_engine.session.post.return_value.__aenter__.return_value = mock_response

        result = await tts_engine._synthesize_aivis("Hello")
        assert result is None


class TestSynthesize:
    """Test main synthesize method."""

    @pytest.mark.asyncio
    async def test_synthesize_voicevox_route(self, tts_engine):
        """Synthesize should route to VOICEVOX."""
        tts_engine.engine_type = "voicevox"
        tts_engine._synthesize_voicevox = AsyncMock(return_value="/tmp/audio.wav")

        result = await tts_engine.synthesize("Hello")

        assert result == "/tmp/audio.wav"
        tts_engine._synthesize_voicevox.assert_called_once_with("Hello")

    @pytest.mark.asyncio
    async def test_synthesize_aivis_route(self, tts_engine):
        """Synthesize should route to AivisSpeech."""
        tts_engine.engine_type = "aivis"
        tts_engine._synthesize_aivis = AsyncMock(return_value="/tmp/audio.wav")

        result = await tts_engine.synthesize("Hello")

        assert result == "/tmp/audio.wav"
        tts_engine._synthesize_aivis.assert_called_once_with("Hello")

    @pytest.mark.asyncio
    async def test_synthesize_empty_text(self, tts_engine):
        """Synthesize should handle empty text."""
        result = await tts_engine.synthesize("")
        assert result is None

    @pytest.mark.asyncio
    async def test_synthesize_with_user_settings(self, tts_engine):
        """Synthesize should apply user settings."""
        tts_engine.engine_type = "aivis"
        tts_engine._synthesize_aivis = AsyncMock(return_value="/tmp/audio.wav")

        user_settings = {"engine": "voicevox", "speaker": "sexy", "speed": 1.2}

        # Should switch to voicevox with settings
        tts_engine._synthesize_voicevox = AsyncMock(return_value="/tmp/audio_vv.wav")

        with patch.object(tts_engine, "_apply_user_settings") as mock_apply:
            await tts_engine.synthesize("Hello", user_settings=user_settings)
            mock_apply.assert_called_once_with(user_settings)


class TestCleanup:
    """Test cleanup functionality."""

    @pytest.mark.asyncio
    async def test_cleanup_closes_session(self, tts_engine):
        """Cleanup should close aiohttp session."""
        mock_session = AsyncMock()
        tts_engine.session = mock_session

        await tts_engine.cleanup()

        mock_session.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_cleanup_handles_no_session(self):
        """Cleanup should handle missing session gracefully."""
        engine = TTSEngine()
        engine.session = None

        # Should not raise
        await engine.cleanup()


class TestUserSettings:
    """Test user settings application."""

    def test_apply_user_settings_engine_switch(self, tts_engine):
        """User settings should switch engine type."""
        tts_engine.engine_type = "aivis"
        tts_engine._apply_user_settings({"engine": "voicevox"})
        assert tts_engine.engine_type == "voicevox"

    def test_apply_user_settings_speaker_change(self, tts_engine):
        """User settings should change speaker."""
        tts_engine.engine_type = "voicevox"
        tts_engine._apply_user_settings({"speaker": "tsun"})
        assert tts_engine.speaker_id == 7  # tsun speaker ID for voicevox

    def test_apply_user_settings_speed_scale(self, tts_engine):
        """User settings should update speed scale."""
        tts_engine._apply_user_settings({"speed": 1.5})
        assert tts_engine.speed_scale == 1.5

    def test_apply_user_settings_volume_scale(self, tts_engine):
        """User settings should update volume scale."""
        tts_engine._apply_user_settings({"volume": 0.8})
        assert tts_engine.volume_scale == 0.8


class TestAudioConversion:
    """Test audio conversion for Discord."""

    @pytest.mark.asyncio
    async def test_convert_to_discord_format(self, tts_engine):
        """Audio should be converted to Discord format."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)

            result = tts_engine._convert_to_discord_format("/tmp/input.wav", "/tmp/output.wav")

            assert result is True
            mock_run.assert_called_once()
            # Check ffmpeg arguments
            args = mock_run.call_args[0][0]
            assert "ffmpeg" in args[0]
            assert "-ar" in args
            assert "48000" in args  # Discord sample rate
            assert "-ac" in args
            assert "2" in args  # Stereo

    @pytest.mark.asyncio
    async def test_convert_to_discord_format_failure(self, tts_engine):
        """Conversion failure should be handled."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1)

            result = tts_engine._convert_to_discord_format("/tmp/input.wav", "/tmp/output.wav")

            assert result is False
