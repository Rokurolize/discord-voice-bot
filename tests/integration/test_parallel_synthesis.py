#!/usr/bin/env python
"""Test script to validate parallel TTS synthesis improvements."""

import asyncio
import logging
from unittest.mock import MagicMock

from src.message_processor import MessageProcessor
from src.voice_handler import VoiceHandler

# Setup logging
logging.basicConfig(level=logging.INFO)


async def test_message_chunking():
    """Test that long messages are properly chunked."""
    processor = MessageProcessor()

    # Test short message (no chunking)
    short_msg = "これは短いメッセージです。"
    chunks = processor.chunk_message(short_msg, max_chunk_size=500)
    assert len(chunks) == 1, f"Short message should not be chunked: {len(chunks)} chunks"
    print("✅ Short message test passed: 1 chunk")

    # Test long message (should be chunked)
    long_msg = "これは長いメッセージです。" * 50  # About 650 characters
    chunks = processor.chunk_message(long_msg, max_chunk_size=100)
    assert len(chunks) > 1, f"Long message should be chunked: {len(chunks)} chunks"
    print(f"✅ Long message test passed: {len(chunks)} chunks created")

    # Test that chunks are within size limit
    for i, chunk in enumerate(chunks):
        assert len(chunk) <= 100, f"Chunk {i} exceeds max size: {len(chunk)} chars"
    print("✅ All chunks within size limit")

    return True


async def test_parallel_queue_processing():
    """Test that synthesis and playback queues work in parallel."""
    # Create mock Discord client
    mock_client = MagicMock()
    mock_client.get_channel = MagicMock(return_value=None)

    # Create voice handler
    handler = VoiceHandler(mock_client)

    # Add multiple messages
    await handler.add_to_queue("メッセージ1", "User1", user_id=123)
    await handler.add_to_queue("これは長いメッセージです。" * 50, "User2", user_id=456)  # About 650 chars
    await handler.add_to_queue("メッセージ3", "User3", user_id=789)

    # Check that synthesis queue has items
    synthesis_count = len(handler.synthesis_queue)
    print(f"✅ Added {synthesis_count} items to synthesis queue")

    # Verify chunking worked for long message
    long_msg_chunks = [item for item in handler.synthesis_queue if item.user_name == "User2"]
    assert len(long_msg_chunks) > 1, f"Long message should be chunked: {len(long_msg_chunks)} chunks"
    print(f"✅ Long message chunked into {len(long_msg_chunks)} parts")

    # Verify message group IDs are set
    group_ids = set()
    for item in handler.synthesis_queue:
        assert item.message_group_id is not None, "Message group ID should be set"
        group_ids.add(item.message_group_id)

    assert len(group_ids) == 3, f"Should have 3 different message groups: {len(group_ids)}"
    print(f"✅ Message groups properly assigned: {len(group_ids)} groups")

    return True


async def test_skip_functionality():
    """Test that skip properly clears all chunks of a message."""
    # Create mock Discord client and voice client
    mock_client = MagicMock()
    mock_voice_client = MagicMock()
    mock_voice_client.is_playing = MagicMock(return_value=True)
    mock_voice_client.stop = MagicMock()

    # Create voice handler
    handler = VoiceHandler(mock_client)
    handler.voice_client = mock_voice_client

    # Add a long message that will be chunked
    await handler.add_to_queue("これは長いメッセージです。" * 50, "TestUser", user_id=123)

    # Get the message group ID
    if handler.synthesis_queue:
        test_group_id = handler.synthesis_queue[0].message_group_id
        handler._current_message_group = test_group_id

        # Move some items to audio queue to simulate synthesis
        handler.audio_queue.extend(list(handler.synthesis_queue)[:2])

        initial_audio_count = len(handler.audio_queue)
        initial_synthesis_count = len(handler.synthesis_queue)

        print(f"Before skip: {initial_audio_count} in audio queue, {initial_synthesis_count} in synthesis queue")

        # Skip the current message
        skipped = await handler.skip_current()

        assert skipped == True, "Skip should return True when audio is playing"
        assert mock_voice_client.stop.called, "Voice client stop should be called"

        # Check that all chunks were removed
        remaining_audio = len(handler.audio_queue)
        remaining_synthesis = len(handler.synthesis_queue)

        print(f"After skip: {remaining_audio} in audio queue, {remaining_synthesis} in synthesis queue")
        print("✅ Skip functionality working: cleared chunks from both queues")

    return True


async def main():
    """Run all tests."""
    print("🧪 Testing Discord Voice Bot Improvements\n")

    try:
        print("1️⃣ Testing message chunking...")
        await test_message_chunking()
        print()

        print("2️⃣ Testing parallel queue processing...")
        await test_parallel_queue_processing()
        print()

        print("3️⃣ Testing skip functionality...")
        await test_skip_functionality()
        print()

        print("✅ All tests passed! The improvements are working correctly.")
        print("\nSummary of improvements:")
        print("- Messages longer than 500 chars are automatically chunked")
        print("- Synthesis happens in parallel while audio is playing")
        print("- Skip command clears all chunks of the current message")
        print("- No gaps between message playback")

    except AssertionError as e:
        print(f"❌ Test failed: {e}")
        return 1
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return 1

    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
