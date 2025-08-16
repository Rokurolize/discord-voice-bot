#!/usr/bin/env python3
"""Test engine mapping for user voices."""

import asyncio

from loguru import logger
from src.config import config
from src.tts_engine import tts_engine
from src.user_settings import user_settings

# Enable detailed logging
logger.remove()
logger.add(lambda msg: print(msg, end=""), level="INFO", colorize=True)


async def test_engine_mapping():
    """Test that engine mapping works correctly."""
    print("\n=== Engine Mapping Test ===\n")
    
    # Show current engine
    print(f"Current TTS Engine: {config.tts_engine}")
    print(f"API URL: {config.api_url}\n")
    
    # Test user 729142264303059065 (VOICEVOX amai) on AIVIS engine
    test_user = "729142264303059065"
    
    print(f"Testing user {test_user}:")
    
    # Get raw settings
    raw_settings = user_settings.get_user_settings(test_user)
    print(f"  Raw settings: {raw_settings}")
    
    # Get speaker for current engine (AIVIS)
    current_engine = config.tts_engine
    speaker_id = user_settings.get_user_speaker(test_user, current_engine)
    print(f"  Speaker ID for {current_engine}: {speaker_id}")
    
    # Initialize TTS engine
    await tts_engine.start()
    
    # Test synthesis
    test_text = "これはエンジンマッピングのテストです"
    print(f"\nSynthesizing with speaker_id={speaker_id}:")
    print(f"  Text: {test_text}")
    
    try:
        audio_data = await tts_engine.synthesize_audio(test_text, speaker_id)
        if audio_data:
            print(f"  ✅ Successfully synthesized {len(audio_data)} bytes")
            
            # Save for inspection
            output_file = f"/tmp/engine_mapping_test_{current_engine}_{speaker_id}.wav"
            with open(output_file, "wb") as f:
                f.write(audio_data)
            print(f"  Saved to: {output_file}")
        else:
            print(f"  ❌ Failed to synthesize audio")
    except Exception as e:
        print(f"  ❌ Error: {e}")
        logger.exception("Synthesis error:")
    
    # Test the other user (176716772664279040)
    print(f"\n---")
    test_user2 = "176716772664279040"
    print(f"Testing user {test_user2}:")
    
    raw_settings2 = user_settings.get_user_settings(test_user2)
    print(f"  Raw settings: {raw_settings2}")
    
    speaker_id2 = user_settings.get_user_speaker(test_user2, current_engine)
    print(f"  Speaker ID for {current_engine}: {speaker_id2}")
    
    # Test synthesis
    try:
        audio_data = await tts_engine.synthesize_audio(test_text, speaker_id2)
        if audio_data:
            print(f"  ✅ Successfully synthesized {len(audio_data)} bytes")
        else:
            print(f"  ❌ Failed to synthesize audio")
    except Exception as e:
        print(f"  ❌ Error: {e}")
    
    # Show compatibility info
    print(f"\n=== Engine Compatibility Info ===")
    compat_info = user_settings.get_engine_compatibility_info(current_engine)
    print(f"Current engine: {compat_info['current_engine']}")
    print(f"Compatible users: {compat_info['total_compatible']}")
    print(f"Mapped users: {compat_info['total_mapped']}")
    
    if compat_info['mapped_users']:
        print(f"\nMapped users detail:")
        for user in compat_info['mapped_users']:
            print(f"  User {user['user_id']}:")
            print(f"    Original: {user['speaker_name']} (ID: {user['original_speaker_id']}, Engine: {user['original_engine']})")
            print(f"    Mapped to: ID {user['mapped_speaker_id']} on {user['current_engine']}")
    
    # Cleanup
    if tts_engine._session:
        await tts_engine._session.close()
    
    print("\n=== Test Complete ===")


if __name__ == "__main__":
    asyncio.run(test_engine_mapping())