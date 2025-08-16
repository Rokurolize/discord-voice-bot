#!/usr/bin/env python3
"""Test multiple pitch correction solutions."""

import asyncio

from src.audio_debugger import audio_debugger
from src.tts_engine import tts_engine


async def test_pitch_solutions():
    """Test various approaches to fix high-pitched voice."""
    print("🔧 Testing Multiple Pitch Correction Solutions")

    await tts_engine.start()

    test_message = "ピッチテスト：この音声が自然な高さに聞こえるかテスト中です。"

    # Test 1: Different Speakers (Anneli vs Zundamon)
    print("\\n📊 Test 1: Speaker Comparison (Anneli vs Zundamon)")
    speakers_to_test = [
        (888753760, "Anneli Normal", "non-zundamon"),
        (1512153250, "Zunda Normal", "zundamon"),
    ]

    for speaker_id, description, category in speakers_to_test:
        print(f"\\n🎤 Testing {description} (ID: {speaker_id})...")
        try:
            audio_source = await tts_engine.create_audio_source(test_message, speaker_id)
            if audio_source:
                print(f"✅ Audio created for {description}")
                tts_engine.cleanup_audio_source(audio_source)
            else:
                print(f"❌ Failed to create audio for {description}")
        except Exception as e:
            print(f"❌ Error with {description}: {e}")

    # Test 2: Pitch Scaling Modification
    print("\\n🎵 Test 2: Aggressive Pitch Scaling")

    # Temporarily modify the TTS engine's pitch optimization
    original_optimize = tts_engine._optimize_audio_parameters

    def aggressive_pitch_optimize(audio_query):
        """Aggressive pitch reduction."""
        if not audio_query:
            return

        # Set optimal sample rate for Discord (48kHz)
        from src.config import config

        audio_query["outputSamplingRate"] = config.audio_sample_rate

        # Adjust volume to prevent clipping
        if "volumeScale" in audio_query:
            audio_query["volumeScale"] = min(1.0, audio_query["volumeScale"] * 0.8)

        # Keep reasonable speed
        if "speedScale" in audio_query:
            audio_query["speedScale"] = max(0.8, min(1.2, audio_query["speedScale"]))

        # AGGRESSIVE pitch reduction
        audio_query["pitchScale"] = 0.6  # Force very low pitch
        print("🔧 Forced pitchScale to 0.6 for aggressive pitch reduction")

    # Replace the optimization temporarily
    tts_engine._optimize_audio_parameters = aggressive_pitch_optimize

    try:
        print("\\n🎤 Testing with aggressive pitch reduction (pitchScale=0.6)...")
        audio_source = await tts_engine.create_audio_source(test_message, 1512153250)  # zunda_normal
        if audio_source:
            print("✅ Audio created with aggressive pitch reduction")
            tts_engine.cleanup_audio_source(audio_source)
        else:
            print("❌ Failed with aggressive pitch reduction")
    except Exception as e:
        print(f"❌ Error with pitch reduction: {e}")
    finally:
        # Restore original optimization
        tts_engine._optimize_audio_parameters = original_optimize

    # Test 3: Check what parameters are actually being sent
    print("\\n🔍 Test 3: Audio Query Parameter Analysis")

    try:
        # Generate audio query to see default parameters
        audio_query = await tts_engine._generate_audio_query(test_message, 1512153250)
        if audio_query:
            print("📋 Raw audio_query parameters from AivisSpeech:")
            interesting_params = [
                "pitchScale",
                "speedScale",
                "volumeScale",
                "outputSamplingRate",
            ]
            for param in interesting_params:
                value = audio_query.get(param, "NOT_SET")
                print(f"   {param}: {value}")

            # Show additional parameters for analysis
            print("\\n📋 All audio_query parameters:")
            for key, value in audio_query.items():
                if key not in interesting_params:
                    print(f"   {key}: {value}")
        else:
            print("❌ Failed to get audio_query")
    except Exception as e:
        print(f"❌ Error getting audio_query: {e}")

    await tts_engine.close()

    # Show debug summary
    summary = audio_debugger.get_session_summary()
    print("\\n📊 Debug Summary:")
    print(f'   Session: {summary["session_id"]}')
    print(f'   Files saved: {summary["total_files"]}')
    print(f'   Debug directory: {summary["session_dir"]}')
    print("\\n🎧 Listen to the debug files to compare pitch differences!")


if __name__ == "__main__":
    asyncio.run(test_pitch_solutions())
