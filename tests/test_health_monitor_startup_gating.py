import time

import pytest


class _FakeConfigManager:
    def __init__(self, channel_id: int = 0) -> None:
        self._cid = channel_id

    def get_target_voice_channel_id(self) -> int:  # pragma: no cover - trivial
        return self._cid


class _FakeTTSClient:
    async def check_api_availability(self) -> tuple[bool, str]:
        return True, ""


class _FakeVoiceHandler:
    def __init__(self, connected: bool) -> None:
        self._connected = connected

    def get_status(self) -> dict[str, object]:
        return {"connected": self._connected, "audio_playback_ready": self._connected}


class _FakeBot:
    def __init__(self, ready: bool, guilds: list = None, voice_handler=None) -> None:
        self._ready = ready
        self.guilds = guilds or []
        self.voice_handler = voice_handler

    # Some discord.py versions use method is_ready(), ensure our fake covers both
    def is_ready(self) -> bool:  # pragma: no cover - trivial
        return self._ready

    def get_channel(self, _cid: int):  # pragma: no cover - trivial
        return None


@pytest.mark.asyncio
async def test_health_monitor_suppresses_warnings_when_not_ready(monkeypatch):
    from discord_voice_bot.health_monitor import HealthMonitor

    bot = _FakeBot(ready=False, guilds=[], voice_handler=_FakeVoiceHandler(connected=False))
    hm = HealthMonitor(bot, _FakeConfigManager(123456789), _FakeTTSClient())
    # Force start timestamp to "now" to simulate grace window
    if hasattr(hm, "_start_ts"):
        hm._start_ts = time.time()

    await hm.perform_health_checks_for_testing()
    assert hm.status.healthy is True
    assert hm.status.issues == []


@pytest.mark.asyncio
async def test_health_monitor_reports_voice_issue_after_ready(monkeypatch):
    from discord_voice_bot.health_monitor import HealthMonitor

    bot = _FakeBot(ready=True, guilds=[object()], voice_handler=_FakeVoiceHandler(connected=False))
    hm = HealthMonitor(bot, _FakeConfigManager(123456789), _FakeTTSClient())
    # Simulate outside grace window if implemented
    if hasattr(hm, "_start_ts"):
        hm._start_ts = time.time() - 60

    await hm.perform_health_checks_for_testing()
    assert hm.status.healthy is False
    # Should include the voice connection issue when ready
    assert any("Voice connection lost" in s for s in hm.status.issues)
