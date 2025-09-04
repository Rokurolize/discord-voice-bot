import discord

from discord_voice_bot.voice.connection_manager import VoiceConnectionManager


class DummyConfigManager:
    def __init__(self, cls: type[discord.VoiceProtocol] | None) -> None:
        self._cls = cls

    def get_voice_client_class(self) -> type[discord.VoiceProtocol] | None:
        return self._cls


def test_get_voice_client_class_returns_override() -> None:
    class MyVoiceClient(discord.VoiceClient):  # pragma: no cover - not instantiated
        pass

    client = discord.Client(intents=discord.Intents.none())
    vcm = VoiceConnectionManager(client, DummyConfigManager(MyVoiceClient))

    resolved = vcm._get_voice_client_class()
    assert resolved is MyVoiceClient


def test_get_voice_client_class_none_when_absent() -> None:
    client = discord.Client(intents=discord.Intents.none())
    vcm = VoiceConnectionManager(client, object())  # type: ignore[arg-type]
    assert vcm._get_voice_client_class() is None
