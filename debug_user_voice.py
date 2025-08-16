#!/usr/bin/env python3
"""Debug script to test user-specific voice synthesis."""

import asyncio
import json
from pathlib import Path

from loguru import logger
from src.config import config
from src.tts_engine import tts_engine
from src.user_settings import user_settings

# Enable debug logging
logger.remove()
logger.add(lambda msg: print(msg, end=""), level="DEBUG", colorize=True)


async def main():
    """Test user voice synthesis with detailed logging."""
    print("\n=== User Voice Debug Script ===\n")
    
    # Check user settings file
    settings_file = Path("/home/ubuntu/.config/discord-voice-bot/user_settings.json")
    print(f"Settings file: {settings_file}")
    print(f"File exists: {settings_file.exists()}")
    
    if settings_file.exists():
        with open(settings_file) as f:
            settings_data = json.load(f)
        print(f"\nSettings content:\n{json.dumps(settings_data, indent=2, ensure_ascii=False)}\n")
    
    # Test user settings module
    print("\n=== Testing UserSettings Module ===")
    
    test_user_id = "729142264303059065"
    speaker_id = user_settings.get_user_speaker(test_user_id)
    user_data = user_settings.get_user_settings(test_user_id)
    
    print(f"User ID: {test_user_id}")
    print(f"Speaker ID from settings: {speaker_id}")
    print(f"Full user data: {user_data}")
    
    # Check current TTS configuration
    print(f"\n=== Current TTS Configuration ===")
    print(f"TTS Engine: {config.tts_engine}")
    print(f"Default API URL: {config.api_url}")
    print(f"Default Speaker: {config.tts_speaker} (ID: {config.speaker_id})")
    
    # Test TTS synthesis with user-specific voice
    print(f"\n=== Testing TTS Synthesis ===")
    
    await tts_engine.start()
    
    # Test with VOICEVOX speaker ID 1 (あまあま)
    test_text = "これはVOICEVOXのあまあまずんだもんのテストです"
    
    print(f"\nTest 1: Using speaker_id=1 (VOICEVOX あまあま)")
    print(f"Text: {test_text}")
    
    try:
        # Temporarily set engine to VOICEVOX for this test
        original_engine = config.tts_engine
        config.tts_engine = "voicevox"
        
        audio_data = await tts_engine.synthesize_audio(test_text, speaker_id=1)
        
        if audio_data:
            print(f"✅ Successfully synthesized {len(audio_data)} bytes")
            # Save for inspection
            output_file = Path("/tmp/voicevox_amai_test.wav")
            with open(output_file, "wb") as f:
                f.write(audio_data)
            print(f"Saved to: {output_file}")
        else:
            print("❌ Failed to synthesize audio")
            
    except Exception as e:
        print(f"❌ Error during synthesis: {e}")
        logger.exception("Synthesis error details:")
    finally:
        config.tts_engine = original_engine
    
    # Test with current engine (AIVIS)
    print(f"\nTest 2: Using current engine ({config.tts_engine})")
    print(f"Default speaker_id: {config.speaker_id}")
    
    try:
        audio_data = await tts_engine.synthesize_audio(test_text)
        if audio_data:
            print(f"✅ Successfully synthesized {len(audio_data)} bytes")
        else:
            print("❌ Failed to synthesize audio")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Test the actual synthesis path for the user
    print(f"\n=== Testing Actual User Voice Path ===")
    
    # This simulates what happens when the bot processes a message from the user
    print(f"When user {test_user_id} sends a message:")
    print(f"1. Bot checks user_settings.get_user_speaker('{test_user_id}')")
    print(f"   Result: {speaker_id}")
    
    if speaker_id:
        print(f"2. Bot should use speaker_id={speaker_id} for synthesis")
        print(f"3. But current engine is {config.tts_engine}, not voicevox")
        print(f"   ⚠️  Problem: Speaker ID 1 is for VOICEVOX, but engine is {config.tts_engine}!")
        
        # Check if this speaker ID exists in current engine
        current_engine_speakers = config.engines[config.tts_engine]["speakers"]
        if speaker_id in current_engine_speakers.values():
            print(f"   Speaker ID {speaker_id} exists in {config.tts_engine}")
        else:
            print(f"   ❌ Speaker ID {speaker_id} does NOT exist in {config.tts_engine}")
            print(f"   Available speakers in {config.tts_engine}:")
            for name, sid in current_engine_speakers.items():
                print(f"      - {name}: {sid}")
    
    # Cleanup
    if tts_engine._session:
        await tts_engine._session.close()
    
    print("\n=== Debug Complete ===")


if __name__ == "__main__":
    asyncio.run(main())