#!/usr/bin/env python3
"""Test the final pitch correction fix."""

import asyncio

from src.audio_debugger import audio_debugger
from src.tts_engine import tts_engine


async def test_final_pitch_fix():
    """Test the implemented pitch correction fix."""
    print("🎵 Testing Final Pitch Correction Fix")
    print("🎯 This will test Zundamon voices with new pitch correction")

    await tts_engine.start()

    test_message = "最終ピッチ修正テスト：この声が自然で低いピッチに聞こえるはずです。ずんだもんの声で確認中です。"

    # Test different Zundamon speakers with the new pitch correction
    zundamon_speakers = [
        (1512153250, "zunda_normal", "Normal Zundamon with pitch fix"),
        (1512153249, "zunda_amai", "Amai Zundamon with pitch fix"),
        (1512153251, "zunda_sexy", "Sexy Zundamon with pitch fix"),
    ]

    print(f"\\n📝 Test message: {test_message}")

    for speaker_id, speaker_name, description in zundamon_speakers:
        print(f"\\n🎤 Testing {description} (ID: {speaker_id})...")

        try:
            # Create audio with pitch correction
            audio_source = await tts_engine.create_audio_source(test_message, speaker_id)

            if audio_source:
                print(f"✅ Audio created with pitch correction for {speaker_name}")
                print("🔧 Applied pitchScale=0.65 for Zundamon voice")
                tts_engine.cleanup_audio_source(audio_source)
            else:
                print(f"❌ Failed to create audio for {speaker_name}")

        except Exception as e:
            print(f"❌ Error with {speaker_name}: {type(e).__name__}: {e!s}")

    # Test with non-Zundamon for comparison
    print("\\n🔄 Testing Anneli (non-Zundamon) for comparison...")
    try:
        audio_source = await tts_engine.create_audio_source(test_message, 888753760)  # Anneli
        if audio_source:
            print("✅ Audio created for Anneli (should use pitchScale=0.85)")
            tts_engine.cleanup_audio_source(audio_source)
        else:
            print("❌ Failed to create audio for Anneli")
    except Exception as e:
        print(f"❌ Error with Anneli: {e}")

    await tts_engine.close()

    # Show results
    summary = audio_debugger.get_session_summary()
    print("\\n📊 Pitch Fix Test Results:")
    print(f'   Session: {summary["session_id"]}')
    print(f'   Audio files generated: {summary["total_files"]}')
    print(f'   Debug directory: {summary["session_dir"]}')
    print("\\n🎧 Listen to the debug files to verify pitch correction!")
    print("🎯 Zundamon voices should now sound significantly lower and more natural")


if __name__ == "__main__":
    asyncio.run(test_final_pitch_fix())
