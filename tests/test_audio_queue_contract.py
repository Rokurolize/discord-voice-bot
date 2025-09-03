import pytest


@pytest.mark.asyncio
async def test_priority_audio_queue_accepts_legacy_and_returns_5_tuple():
    from discord_voice_bot.voice.queues import PriorityAudioQueue

    q = PriorityAudioQueue()

    # Legacy 4-tuple
    await q.put(("/tmp/a.wav", "g1", 5, 0))
    # New 5-tuple
    await q.put(("/tmp/b.wav", "g2", 1, 0, 123))

    # Priority 1 comes first
    item1 = await q.get()
    assert isinstance(item1, tuple) and len(item1) == 5
    path1, group1, prio1, idx1, size1 = item1
    assert path1.endswith("b.wav") and prio1 == 1 and size1 == 123

    # Next legacy item should have audio_size defaulted to 0
    item2 = await q.get()
    assert isinstance(item2, tuple) and len(item2) == 5
    path2, group2, prio2, idx2, size2 = item2
    assert path2.endswith("a.wav") and prio2 == 5 and size2 == 0
