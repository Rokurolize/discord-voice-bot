#!/usr/bin/env python3
"""Test dynamic settings reload functionality."""

import asyncio
import json
import time
from pathlib import Path

from loguru import logger
from src.config import config
from src.tts_engine import tts_engine
from src.user_settings import user_settings

# Enable detailed logging
logger.remove()
logger.add(lambda msg: print(msg, end=""), level="INFO", colorize=True)


async def test_dynamic_settings():
    """Test that settings changes are reflected dynamically."""
    print("\n=== Dynamic Settings Test ===\n")
    
    settings_file = Path("/home/ubuntu/.config/discord-voice-bot/user_settings.json")
    
    # Test user
    test_user = "176716772664279040"
    
    print(f"Testing user {test_user}:")
    
    # Step 1: Check current settings
    print("\n--- Step 1: Initial Settings ---")
    current = user_settings.get_user_speaker(test_user, config.tts_engine)
    settings = user_settings.get_user_settings(test_user)
    print(f"Current speaker ID: {current}")
    print(f"Full settings: {settings}")
    
    # Step 2: Modify the settings file directly
    print("\n--- Step 2: Modifying Settings File ---")
    
    with open(settings_file, "r") as f:
        data = json.load(f)
    
    # Save original
    original_speaker = data[test_user]["speaker_id"]
    original_name = data[test_user]["speaker_name"]
    
    # Change to different speaker
    if data[test_user]["speaker_id"] == 1:
        # Change to normal if currently amai
        data[test_user]["speaker_id"] = 3
        data[test_user]["speaker_name"] = "ずんだもん（ノーマル）"
    else:
        # Change to amai
        data[test_user]["speaker_id"] = 1
        data[test_user]["speaker_name"] = "ずんだもん（あまあま）"
    
    with open(settings_file, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    print(f"Changed speaker from {original_name} (ID: {original_speaker})")
    print(f"                 to {data[test_user]['speaker_name']} (ID: {data[test_user]['speaker_id']})")
    
    # Step 3: Check if change is reflected
    print("\n--- Step 3: Checking Dynamic Reload ---")
    
    # Small delay to ensure file write is complete
    await asyncio.sleep(0.1)
    
    new_speaker = user_settings.get_user_speaker(test_user, config.tts_engine)
    new_settings = user_settings.get_user_settings(test_user)
    
    print(f"New speaker ID: {new_speaker}")
    print(f"Full settings: {new_settings}")
    
    if new_speaker != original_speaker:
        print("✅ Dynamic reload successful! Settings changed without restart.")
    else:
        print("❌ Dynamic reload failed. Settings not updated.")
    
    # Step 4: Test synthesis with new voice
    print("\n--- Step 4: Testing Synthesis ---")
    
    await tts_engine.start()
    
    test_text = "設定が動的に変更されました"
    print(f"Synthesizing with speaker_id={new_speaker}: {test_text}")
    
    try:
        audio_data = await tts_engine.synthesize_audio(test_text, new_speaker)
        if audio_data:
            print(f"✅ Successfully synthesized {len(audio_data)} bytes")
        else:
            print("❌ Failed to synthesize")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Step 5: Restore original settings
    print("\n--- Step 5: Restoring Original Settings ---")
    
    data[test_user]["speaker_id"] = original_speaker
    data[test_user]["speaker_name"] = original_name
    
    with open(settings_file, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    print(f"Restored to {original_name} (ID: {original_speaker})")
    
    # Cleanup
    if tts_engine._session:
        await tts_engine._session.close()
    
    print("\n=== Test Complete ===")


if __name__ == "__main__":
    asyncio.run(test_dynamic_settings())