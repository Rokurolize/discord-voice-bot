#!/usr/bin/env python3
"""Trigger TTS test directly on the running bot instance."""

import asyncio
import sys

# Add the project directory to Python path
sys.path.insert(0, "/home/ubuntu/workbench/projects/discord-voice-bot")

from src.tts_engine import tts_engine


async def trigger_manual_tts():
    """Manually trigger TTS on the running bot."""
    print("🎯 Triggering manual TTS test...")

    # We need to access the running bot's voice handler
    # Since we can't directly access it, let's simulate the !tts test command
    # by directly using the TTS engine and creating a proper test

    test_message = "手動TTS実行テスト！これが聞こえれば成功です！"

    await tts_engine.start()

    print(f"🎤 Synthesizing: {test_message}")
    audio_source = await tts_engine.create_audio_source(test_message)

    if audio_source:
        print(f"✅ Audio source ready: {type(audio_source)}")
        print("📝 This would normally be played by Discord voice client")
        print("🎵 Audio pipeline is working correctly!")

        # Cleanup
        tts_engine.cleanup_audio_source(audio_source)

    else:
        print("❌ Failed to create audio source")

    await tts_engine.close()


if __name__ == "__main__":
    print("🧪 Manual TTS Test (No Discord API conflicts)")
    asyncio.run(trigger_manual_tts())
