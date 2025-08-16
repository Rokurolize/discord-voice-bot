#!/usr/bin/env python3
"""Test the fixed TTS engine without pitch modifications."""

import asyncio
from pathlib import Path

from src.tts_engine import tts_engine


async def test_fixed_voices():
    """Test that removing pitch modifications fixes the high-pitched voice issue."""
    print("🔧 Testing Fixed TTS Engine (No Pitch Modifications)")
    print("🎯 All voices should now sound normal and natural\n")

    await tts_engine.start()

    test_text = "修正後テスト：この音声が自然に聞こえるはずです。ピッチ修正を削除しました。"
    output_dir = Path("/tmp/fixed_voice_test")
    output_dir.mkdir(exist_ok=True)

    # Test the speakers that were previously high-pitched
    test_speakers = [
        (1512153249, "zunda_amai_fixed"),
        (1512153250, "zunda_normal_fixed"),
        (888753760, "anneli_normal_fixed"),
    ]

    for speaker_id, name in test_speakers:
        print(f"🎤 Testing {name} (Speaker ID: {speaker_id})")

        try:
            # Create audio with the fixed TTS engine (no pitch modifications)
            audio_source = await tts_engine.create_audio_source(test_text, speaker_id)

            if audio_source:
                print("✅ Audio created successfully")

                # Since we can't directly save the audio source, let's use the debug system
                # The audio will be automatically saved by the audio debugger

                # Cleanup
                tts_engine.cleanup_audio_source(audio_source)
                print("🎵 Voice should sound normal (no high-pitch distortion)")

            else:
                print("❌ Failed to create audio")

        except Exception as e:
            print(f"❌ Error: {type(e).__name__}: {e!s}")

        print()

    await tts_engine.close()

    print("🎯 Fixed Voice Test Results:")
    print("   All generated audio should now sound natural and normal-pitched")
    print("   Check the audio_debugger output files for the actual audio files")

    # Show where the debug files are saved
    from src.audio_debugger import audio_debugger

    summary = audio_debugger.get_session_summary()
    print(f'   Debug files location: {summary["session_dir"]}')
    print(f'   Files generated: {summary["total_files"]}')


if __name__ == "__main__":
    asyncio.run(test_fixed_voices())
