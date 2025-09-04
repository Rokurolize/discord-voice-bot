from __future__ import annotations

from unittest.mock import MagicMock, PropertyMock

from discord_voice_bot.voice.status import build_status


def test_build_status_basic():
    voice_handler = MagicMock()
    voice_handler.voice_client.is_connected.return_value = True
    voice_handler.voice_client.channel.name = "test-channel"
    voice_handler.voice_client.channel.id = 12345
    voice_handler.target_channel = None
    voice_handler.is_playing_flag = True
    voice_handler.synthesis_queue.qsize.return_value = 1
    voice_handler.audio_queue.qsize.return_value = 2
    voice_handler.current_group_id = "group1"
    voice_handler.stats = {"messages_played": 10, "messages_skipped": 1, "errors": 0}
    voice_handler.connection_state = "connected"

    status = build_status(voice_handler)

    assert status["connected"] is True
    assert status["voice_connected"] is True
    assert status["voice_channel_name"] == "test-channel"
    assert status["voice_channel_id"] == 12345
    assert status["playing"] is True
    assert status["synthesis_queue_size"] == 1
    assert status["audio_queue_size"] == 2
    assert status["total_queue_size"] == 3
    assert status["current_group"] == "group1"
    assert status["messages_played"] == 10
    assert status["messages_skipped"] == 1
    assert status["errors"] == 0
    assert status["connection_state"] == "connected"
    assert status["is_playing"] is True
    assert status["max_queue_size"] == 50


def test_build_status_not_connected():
    voice_handler = MagicMock()
    voice_handler.voice_client = None
    voice_handler.target_channel.name = "target-channel"
    voice_handler.target_channel.id = 67890

    status = build_status(voice_handler)

    assert status["connected"] is False
    assert status["voice_channel_name"] == "target-channel"
    assert status["voice_channel_id"] == 67890


def test_build_status_channel_error():
    voice_handler = MagicMock()
    voice_handler.voice_client.is_connected.return_value = True
    type(voice_handler.voice_client).channel = PropertyMock(side_effect=RuntimeError("Test error"))
    voice_handler.target_channel = None

    status = build_status(voice_handler)

    assert status["voice_channel_name"] is None
    assert status["voice_channel_id"] is None


def test_build_status_fallback_playing_flag():
    voice_handler = MagicMock()
    # Configure the mock to not have the 'is_playing_flag' attribute
    delattr(voice_handler, "is_playing_flag")
    voice_handler._is_playing_flag = True

    status = build_status(voice_handler)

    assert status["playing"] is True
    assert status["is_playing"] is True
