#!/usr/bin/env python3
"""Directly trigger TTS on the running bot by accessing the voice handler."""

import asyncio
import sys

# Add project path
sys.path.insert(0, "/home/ubuntu/workbench/projects/discord-voice-bot")

from src.bot import global_voice_handler
from src.message_processor import message_processor


async def trigger_direct_tts():
    """Trigger TTS directly on the running bot."""
    print("🎯 Attempting to trigger TTS on running bot instance...")

    # Check if global voice handler is available
    if global_voice_handler is None:
        print("❌ Global voice handler not available - bot may not be fully initialized")
        return False

    print(f"✅ Found global voice handler: {type(global_voice_handler)}")

    # Check voice connection status
    is_connected = global_voice_handler.is_connected
    print(f"🔗 Voice connected: {is_connected}")

    if not is_connected:
        print("❌ Bot is not connected to voice channel")
        return False

    # Get voice handler status
    status = await global_voice_handler.get_status()
    print("📊 Voice Handler Status:")
    for key, value in status.items():
        print(f"  {key}: {value}")

    # Process test message
    test_text = "直接TTSテストです！これが聞こえれば、音声パイプラインが正常に動作しています！"
    processed_text = message_processor.process_message_content(test_text, "DirectTest")

    print(f"🎤 Queuing TTS: {processed_text}")

    # Add to queue with high priority
    success = await global_voice_handler.add_to_queue(processed_text, "DirectTest", priority=1)  # High priority

    if success:
        print("✅ TTS successfully queued")
        print("🎵 Check Discord voice channel for audio output!")

        # Monitor queue for a bit
        for i in range(10):  # Monitor for 10 seconds
            await asyncio.sleep(1)
            current_status = await global_voice_handler.get_status()
            queue_size = current_status.get("queue_size", 0)
            is_playing = current_status.get("is_playing", False)
            print(f"📊 [{i+1}s] Queue: {queue_size}, Playing: {is_playing}", end="\r")

        print("\n🎯 Direct TTS trigger completed")
        return True
    else:
        print("❌ Failed to queue TTS")
        return False


if __name__ == "__main__":
    print("🧪 Direct TTS Trigger Test")
    try:
        result = asyncio.run(trigger_direct_tts())
        print(f'Final result: {"✅ SUCCESS" if result else "❌ FAILED"}')
    except Exception as e:
        print(f"❌ Test failed with exception: {type(e).__name__}: {e!s}")
        import traceback

        traceback.print_exc()
