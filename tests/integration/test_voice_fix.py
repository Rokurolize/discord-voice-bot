#!/usr/bin/env python3
"""Test voice fix - compare zunda_normal vs zunda_amai speakers."""

import asyncio

from src.audio_debugger import audio_debugger
from src.tts_engine import tts_engine


async def test_voice_comparison():
    """Test both speaker variants to compare voice quality."""
    print("🎤 Testing Voice Fix: zunda_normal vs zunda_amai")

    await tts_engine.start()

    test_message = "音声テスト：この声が自然に聞こえるかチェック中です。ずんだもんの声で読み上げています。"

    # Test 1: Current setting (should be zunda_normal now)
    print("\\n🔄 Testing current speaker setting...")

    # Check current configuration
    from src.config import config

    print(f"📊 Current engine: {config.tts_engine}")
    print(f"📊 Current speaker: {config.tts_speaker}")
    print(f"📊 Current speaker ID: {config.speaker_id}")

    try:
        # Test current configuration
        audio_source1 = await tts_engine.create_audio_source(test_message)
        if audio_source1:
            print("✅ Successfully created audio with current speaker")
            tts_engine.cleanup_audio_source(audio_source1)
        else:
            print("❌ Failed to create audio with current speaker")

        # Test with explicit zunda_amai (old problematic setting) for comparison
        print("\\n🔄 Testing zunda_amai (old high-pitched setting) for comparison...")
        amai_speaker_id = 1512153249  # zunda_amai
        audio_source2 = await tts_engine.create_audio_source(test_message, amai_speaker_id)
        if audio_source2:
            print("✅ Successfully created audio with zunda_amai (high-pitched)")
            tts_engine.cleanup_audio_source(audio_source2)
        else:
            print("❌ Failed to create audio with zunda_amai")

        # Test with explicit zunda_normal for comparison
        print("\\n🔄 Testing zunda_normal (should be lower pitched)...")
        normal_speaker_id = 1512153250  # zunda_normal
        audio_source3 = await tts_engine.create_audio_source(test_message, normal_speaker_id)
        if audio_source3:
            print("✅ Successfully created audio with zunda_normal (normal pitch)")
            tts_engine.cleanup_audio_source(audio_source3)
        else:
            print("❌ Failed to create audio with zunda_normal")

        print("\\n📊 Voice Comparison Summary:")
        print("🎵 Check the debug audio files to compare:")
        summary = audio_debugger.get_session_summary()
        print(f'   Debug directory: {summary["session_dir"]}')
        print(f'   Total files: {summary["total_files"]}')

    except Exception as e:
        print(f"❌ Test failed: {type(e).__name__}: {e!s}")

    await tts_engine.close()


if __name__ == "__main__":
    asyncio.run(test_voice_comparison())
