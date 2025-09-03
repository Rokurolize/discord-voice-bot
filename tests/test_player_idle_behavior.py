import asyncio

import pytest


class _FakeAudioQueue:
    async def get(self):
        # Immediately raise the same exception our PriorityAudioQueue would raise when empty
        import asyncio as _asyncio

        raise _asyncio.QueueEmpty


class _FakeVoiceClient:
    def is_connected(self) -> bool:  # pragma: no cover - trivial
        return False

    def is_playing(self) -> bool:  # pragma: no cover - trivial
        return False


class _FakeStats:
    def increment_errors(self) -> None:  # pragma: no cover - trivial
        return None

    def increment_messages_played(self) -> None:  # pragma: no cover - trivial
        return None


class _FakeVoiceHandler:
    def __init__(self):
        self.audio_queue = _FakeAudioQueue()
        self.voice_client = _FakeVoiceClient()
        self.stats_tracker = _FakeStats()
        self._playing = False
        self.current_group_id = None
        self.synthesizer = None

    @property
    def is_playing_flag(self) -> bool:
        return self._playing

    @is_playing_flag.setter
    def is_playing_flag(self, v: bool) -> None:
        self._playing = bool(v)


@pytest.mark.asyncio
async def test_player_worker_idle_does_not_crash():
    from discord_voice_bot.voice.workers.player import PlayerWorker

    vh = _FakeVoiceHandler()
    worker = PlayerWorker(vh)

    # Run briefly then cancel; ensure no exceptions escape
    task = asyncio.create_task(worker.run())
    await asyncio.sleep(0.2)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
