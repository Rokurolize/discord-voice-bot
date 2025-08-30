#!/usr/bin/env python3
"""Test script to verify TTS engine factory and synthesis behavior."""

import dataclasses
from unittest.mock import AsyncMock, patch

import pytest

from discord_voice_bot.config import Config
from discord_voice_bot.tts_engine import TTSEngine, get_tts_engine


@pytest.mark.asyncio
async def test_tts_engine_factory_and_synthesis(config: Config):
    """Validate `get_tts_engine` factory and core synthesis paths."""
    with (
        patch("discord_voice_bot.tts_engine.TTSEngine._generate_audio_query", new_callable=AsyncMock) as mock_gen_query,
        patch("discord_voice_bot.tts_engine.TTSEngine._synthesize_from_query", new_callable=AsyncMock) as mock_synth_query,
        patch("discord_voice_bot.tts_engine.TTSHealthMonitor.perform_health_check", new_callable=AsyncMock) as mock_health_check,
        patch("discord_voice_bot.tts_engine.TTSClient.start_session", new_callable=AsyncMock) as mock_start_session,
        patch("discord_voice_bot.tts_engine.TTSClient.close_session", new_callable=AsyncMock) as mock_close_session,
    ):
        # Mark mock as used for type checkers
        _ = mock_start_session
        mock_gen_query.return_value = {"mora": "data"}
        mock_synth_query.return_value = b"mock_audio"
        mock_health_check.return_value = True

        # Voicevox by default
        voicevox_config = dataclasses.replace(config, tts_engine="voicevox")
        engine: TTSEngine = await get_tts_engine(voicevox_config)
        assert isinstance(engine, TTSEngine)
        assert engine.engine_name == "voicevox"

        # Default synthesis path
        out = await engine.synthesize_audio("hello")
        assert out == b"mock_audio"
        mock_gen_query.assert_awaited()
        mock_synth_query.assert_awaited()

        # Engine override
        out2 = await engine.synthesize_audio("hello", engine_name="aivis")
        assert out2 == b"mock_audio"

        # Cleanup closes client session
        await engine.close()
        mock_close_session.assert_awaited()
