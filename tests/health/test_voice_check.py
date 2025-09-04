from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from discord_voice_bot.health.voice_check import check_voice_connection_health


@pytest.mark.asyncio
async def test_check_voice_connection_health_no_guild():
    healthy, issues = await check_voice_connection_health(None, MagicMock(), None)
    assert healthy is True
    assert not issues


@pytest.mark.asyncio
async def test_check_voice_connection_health_no_voice_client():
    healthy, issues = await check_voice_connection_health(AsyncMock(), None, None)
    assert healthy is True
    assert not issues


@pytest.mark.asyncio
async def test_check_voice_connection_health_not_connected():
    voice_client = MagicMock()
    voice_client.is_connected.return_value = False
    healthy, issues = await check_voice_connection_health(AsyncMock(), voice_client, None)
    assert healthy is False
    assert "VoiceClient is not connected" in issues


@pytest.mark.asyncio
async def test_check_voice_connection_health_no_channel():
    voice_client = MagicMock()
    voice_client.is_connected.return_value = True
    voice_client.channel = None
    healthy, issues = await check_voice_connection_health(AsyncMock(), voice_client, None)
    assert healthy is False
    assert "VoiceClient has no channel bound" in issues


@pytest.mark.asyncio
async def test_check_voice_connection_health_is_connected_raises():
    voice_client = MagicMock()
    voice_client.is_connected.side_effect = RuntimeError("Test error")
    healthy, issues = await check_voice_connection_health(AsyncMock(), voice_client, None)
    assert healthy is False
    assert "VoiceClient check error: RuntimeError" in issues


@pytest.mark.asyncio
async def test_check_voice_connection_health_state_getter_works():
    voice_client = MagicMock()
    voice_client.is_connected.return_value = True
    voice_client.channel = MagicMock()
    state_getter = MagicMock()
    healthy, issues = await check_voice_connection_health(AsyncMock(), voice_client, state_getter)
    assert healthy is True
    assert not issues
    state_getter.assert_called_once()


@pytest.mark.asyncio
async def test_check_voice_connection_health_state_getter_raises():
    voice_client = MagicMock()
    voice_client.is_connected.return_value = True
    voice_client.channel = MagicMock()
    state_getter = MagicMock(side_effect=ValueError("Test error"))
    healthy, issues = await check_voice_connection_health(AsyncMock(), voice_client, state_getter)
    assert healthy is False
    assert "Connection state getter error: ValueError" in issues


@pytest.mark.asyncio
async def test_check_voice_connection_health_healthy():
    voice_client = MagicMock()
    voice_client.is_connected.return_value = True
    voice_client.channel = MagicMock()
    healthy, issues = await check_voice_connection_health(AsyncMock(), voice_client, None)
    assert healthy is True
    assert not issues
