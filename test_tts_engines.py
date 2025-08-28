#!/usr/bin/env python3
"""Test script to verify TTS engines are working properly."""

import dataclasses
from unittest.mock import AsyncMock, patch

import pytest

from discord_voice_bot.config import Config
from discord_voice_bot.tts_engine import TTSEngine, get_tts_engine


@pytest.mark.asyncio
@patch("discord_voice_bot.tts_engine.VoicevoxClient.synthesize_audio", new_callable=AsyncMock)
@patch("discord_voice_bot.tts_engine.AivisClient.synthesize_audio", new_callable=AsyncMock)
async def test_tts_engine_factory_and_synthesis(
    mock_aivis_synth: AsyncMock, mock_voicevox_synth: AsyncMock, config: Config
):
    """Test the TTSEngine factory and that it can dispatch to the correct engine."""
    # Mock the return value of the synthesizers
    mock_voicevox_synth.return_value = b"voicevox_audio_data"
    mock_aivis_synth.return_value = b"aivis_audio_data"

    # 1. Test the factory function `get_tts_engine`
    voicevox_config = dataclasses.replace(config, tts_engine="voicevox")
    tts_engine: TTSEngine = await get_tts_engine(voicevox_config)
    assert isinstance(tts_engine, TTSEngine)
    assert tts_engine.current_engine_name == "voicevox"

    # 2. Test that it calls the correct underlying client (Voicevox)
    test_text = "This is a test."
    audio_data = await tts_engine.synthesize_audio(test_text)

    assert audio_data == b"voicevox_audio_data"
    mock_voicevox_synth.assert_called_once_with(test_text, "normal")
    mock_aivis_synth.assert_not_called()

    # Reset mocks
    mock_voicevox_synth.reset_mock()
    mock_aivis_synth.reset_mock()

    # 3. Test that we can switch to the other engine (Aivis)
    audio_data_aivis = await tts_engine.synthesize_audio(test_text, engine_name="aivis")

    assert audio_data_aivis == b"aivis_audio_data"
    mock_aivis_synth.assert_called_once_with(test_text, "normal")
    mock_voicevox_synth.assert_not_called()
    assert getattr(tts_engine, "current_engine_name", "aivis") == "aivis"

    # 4. Test cleanup
    with patch.object(tts_engine.voicevox_client.session, "close") as mock_vv_close, patch.object(
        tts_engine.aivis_client.session, "close"
    ) as mock_aivis_close:
        await tts_engine.close()
        mock_vv_close.assert_called_once()
        mock_aivis_close.assert_called_once()
