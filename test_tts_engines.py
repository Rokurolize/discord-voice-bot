#!/usr/bin/env python3
"""Test script to verify TTS engines are working properly."""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from discord_voice_bot.config_manager import ConfigManagerImpl
from discord_voice_bot.tts_engine import get_tts_engine


async def test_tts_engines():
    """Test both TTS engines."""
    print("🔊 Testing TTS Engines...")

    config = ConfigManagerImpl()
    tts_engine = await get_tts_engine(config)

    test_text = "こんにちは、ボットです。正常に動作しています。"

    try:
        # Start the TTS engine session
        print("🔧 Starting TTS engine...")
        await tts_engine.start()
        print("✅ TTS engine started successfully")

        print("🎤 Testing VOICEVOX engine...")
        audio_data = await tts_engine.synthesize_audio(test_text, engine_name="voicevox")
        if audio_data:
            print(f"✅ VOICEVOX synthesis successful! Audio size: {len(audio_data)} bytes")
        else:
            print("❌ VOICEVOX synthesis failed")

        print("🎤 Testing AIVIS engine...")
        audio_data = await tts_engine.synthesize_audio(test_text, engine_name="aivis")
        if audio_data:
            print(f"✅ AIVIS synthesis successful! Audio size: {len(audio_data)} bytes")
        else:
            print("❌ AIVIS synthesis failed")

        # Clean up
        await tts_engine.close()

    except Exception as e:
        print(f"❌ TTS Engine test failed: {e}")
        import traceback

        traceback.print_exc()
        return False

    print("✅ All TTS engine tests completed successfully!")
    return True


if __name__ == "__main__":
    _ = asyncio.run(test_tts_engines())
