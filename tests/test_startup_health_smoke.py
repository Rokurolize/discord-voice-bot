import pytest


class _FakeEngineOK:
    async def start(self) -> None:  # pragma: no cover - trivial
        return None

    async def check_api_availability(self) -> tuple[bool, str]:
        return True, ""

    async def synthesize_audio(self, text: str) -> bytes | None:
        return b"\x00" * 512

    async def close(self) -> None:  # pragma: no cover - trivial
        return None


class _FakeEngineBadAPI:
    async def start(self) -> None:  # pragma: no cover - trivial
        return None

    async def check_api_availability(self) -> tuple[bool, str]:
        return False, "unavailable"

    async def synthesize_audio(self, text: str) -> bytes | None:  # pragma: no cover - trivial
        return None

    async def close(self) -> None:  # pragma: no cover - trivial
        return None


class _FakeEngineWeird:
    async def start(self) -> None:  # pragma: no cover - trivial
        return None

    async def check_api_availability(self):  # type: ignore[no-untyped-def]
        # Return an unexpected shape to ensure guard works
        return {"ok": True}

    async def synthesize_audio(self, text: str) -> bytes | None:  # pragma: no cover - trivial
        return None

    async def close(self) -> None:  # pragma: no cover - trivial
        return None


@pytest.mark.asyncio
async def test_health_check_succeeds_with_fake_engine(monkeypatch):
    import discord_voice_bot.tts_engine as te
    from discord_voice_bot.__main__ import BotManager
    from discord_voice_bot.config import Config

    async def _get_tts_engine(_cfg: Config):
        return _FakeEngineOK()

    monkeypatch.setattr(te, "get_tts_engine", _get_tts_engine, raising=True)

    cfg = Config.from_env()
    bm = BotManager(cfg)
    ok = await bm.health_check()
    assert ok is True


@pytest.mark.asyncio
async def test_health_check_handles_api_failure(monkeypatch):
    import discord_voice_bot.tts_engine as te
    from discord_voice_bot.__main__ import BotManager
    from discord_voice_bot.config import Config

    async def _get_tts_engine(_cfg: Config):
        return _FakeEngineBadAPI()

    monkeypatch.setattr(te, "get_tts_engine", _get_tts_engine, raising=True)

    cfg = Config.from_env()
    bm = BotManager(cfg)
    ok = await bm.health_check()
    assert ok is False


@pytest.mark.asyncio
async def test_health_check_raises_on_unexpected_return_shape(monkeypatch):
    import discord_voice_bot.tts_engine as te
    from discord_voice_bot.__main__ import BotManager
    from discord_voice_bot.config import Config
    from discord_voice_bot.errors import HealthCheckError

    async def _get_tts_engine(_cfg: Config):
        return _FakeEngineWeird()

    monkeypatch.setattr(te, "get_tts_engine", _get_tts_engine, raising=True)

    cfg = Config.from_env()
    bm = BotManager(cfg)
    with pytest.raises(HealthCheckError) as ei:
        _ = await bm.health_check()
    # Ensure message contains structured fields (engine and url at least)
    s = str(ei.value)
    assert "result_type=" in s and "result_repr=" in s
    assert "engine=" in s and "url=" in s


@pytest.mark.asyncio
async def test_health_check_skips_with_flag(monkeypatch):
    import discord_voice_bot.tts_engine as te
    from discord_voice_bot.__main__ import BotManager
    from discord_voice_bot.config import Config

    # Ensure get_tts_engine is NOT called when the flag is set
    def _should_not_be_called(*args, **kwargs):  # type: ignore[no-untyped-def]
        raise AssertionError("get_tts_engine should not be called when STARTUP_SKIP_TTS_CHECK is enabled")

    monkeypatch.setenv("STARTUP_SKIP_TTS_CHECK", "true")
    monkeypatch.setattr(te, "get_tts_engine", _should_not_be_called, raising=True)

    cfg = Config.from_env()
    bm = BotManager(cfg)
    ok = await bm.health_check()
    assert ok is True
