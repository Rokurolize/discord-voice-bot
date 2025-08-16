#!/usr/bin/env python3
"""Test VOICEVOX amai voice directly."""

import asyncio
import os

from loguru import logger
from src.config import config
from src.tts_engine import tts_engine
from src.user_settings import user_settings

# Enable detailed logging
logger.remove()
logger.add(lambda msg: print(msg, end=""), level="INFO", colorize=True)


async def test_voicevox_amai():
    """Test VOICEVOX amai voice."""
    print("\n=== VOICEVOX Amai Test ===\n")
    
    # Force VOICEVOX engine
    original_engine = config.tts_engine
    config.tts_engine = "voicevox"
    
    print(f"TTS Engine: {config.tts_engine}")
    print(f"API URL: {config.api_url}\n")
    
    # Initialize TTS engine
    await tts_engine.start()
    
    # Test with speaker ID 1 (amai)
    test_text = "これはVOICEVOXのあまあまずんだもんです。かわいく話すのだ"
    speaker_id = 1
    
    print(f"Testing speaker_id={speaker_id} (ずんだもん あまあま):")
    print(f"  Text: {test_text}")
    
    try:
        audio_data = await tts_engine.synthesize_audio(test_text, speaker_id)
        if audio_data:
            print(f"  ✅ Successfully synthesized {len(audio_data)} bytes")
            
            # Save for inspection
            output_file = f"/tmp/voicevox_amai_{speaker_id}.wav"
            with open(output_file, "wb") as f:
                f.write(audio_data)
            print(f"  Saved to: {output_file}")
            print(f"  Play with: aplay {output_file}")
        else:
            print(f"  ❌ Failed to synthesize audio")
    except Exception as e:
        print(f"  ❌ Error: {e}")
        logger.exception("Synthesis error:")
    
    # Test user 729142264303059065 with VOICEVOX
    print(f"\n---")
    test_user = "729142264303059065"
    print(f"Testing user {test_user} on VOICEVOX:")
    
    raw_settings = user_settings.get_user_settings(test_user)
    print(f"  Raw settings: {raw_settings}")
    
    # Get speaker for VOICEVOX engine
    speaker_id = user_settings.get_user_speaker(test_user, "voicevox")
    print(f"  Speaker ID for voicevox: {speaker_id}")
    
    if speaker_id:
        try:
            audio_data = await tts_engine.synthesize_audio(test_text, speaker_id)
            if audio_data:
                print(f"  ✅ Successfully synthesized {len(audio_data)} bytes")
            else:
                print(f"  ❌ Failed to synthesize audio")
        except Exception as e:
            print(f"  ❌ Error: {e}")
    
    # Restore original engine
    config.tts_engine = original_engine
    
    # Cleanup
    if tts_engine._session:
        await tts_engine._session.close()
    
    print("\n=== Test Complete ===")


if __name__ == "__main__":
    asyncio.run(test_voicevox_amai())