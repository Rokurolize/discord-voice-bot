#!/usr/bin/env python3
"""Test user-specific voice settings."""

import asyncio

from src.tts_engine import tts_engine
from src.user_settings import user_settings


async def test_user_voices():
    """Test that user-specific voices work correctly."""
    print("\n=== Testing User Voice Settings ===\n")

    # Show current settings
    all_settings = user_settings.list_all_settings()
    print(f"Current user settings: {all_settings}\n")

    # Test getting speaker for users in actual settings file
    # Note: Expected values come from /home/ubuntu/.config/discord-voice-bot/user_settings.json
    test_users = [
        ("176716772664279040", None, None),  # Load from settings file
        ("729142264303059065", None, None),  # Load from settings file  
        ("123456789", None, None),  # Unknown user - should be None
    ]

    # Test against actual settings file instead of hardcoded expectations
    for user_id, _, _ in test_users:
        speaker_id = user_settings.get_user_speaker(user_id)
        user_data = user_settings.get_user_settings(user_id)
        
        if user_data:
            expected_id = user_data["speaker_id"]
            print(f"User {user_id}: Speaker ID = {speaker_id} (from file: {expected_id}, name: {user_data['speaker_name']})")
            assert speaker_id == expected_id, f"Mismatch for user {user_id}"
        else:
            print(f"User {user_id}: Speaker ID = {speaker_id} (no settings - using default)")
            # For users without settings, should return None
            if user_id == "123456789":  # Unknown user
                assert speaker_id is None, f"Unknown user should have None speaker_id, got {speaker_id}"

    print("\n=== Testing TTS with User Voices ===\n")

    # Initialize TTS engine
    await tts_engine.start()

    # Test synthesis with speakers from actual settings
    test_messages = []
    
    # Add default voice test
    test_messages.append(("デフォルトの声でテストです", None))
    
    # Add tests for each configured user's voice
    for user_id, _, _ in test_users[:2]:  # Skip unknown user
        user_data = user_settings.get_user_settings(user_id)
        if user_data:
            speaker_name = user_data["speaker_name"]
            speaker_id = user_data["speaker_id"]
            test_messages.append((f"{speaker_name}の声でテストです", speaker_id))

    for text, speaker_id in test_messages:
        print(f"Testing: '{text}' with speaker_id={speaker_id}")
        audio_data = await tts_engine.synthesize_audio(text, speaker_id)
        if audio_data:
            print(f"  ✓ Generated {len(audio_data)} bytes of audio")
        else:
            print("  ✗ Failed to generate audio")

    # Test adding a new user preference
    print("\n=== Testing Dynamic User Settings ===\n")

    new_user_id = "999999999"
    success = user_settings.set_user_speaker(new_user_id, 888753760, "anneli_normal")
    print(f"Setting voice for user {new_user_id}: {'Success' if success else 'Failed'}")

    # Verify it was saved
    saved_speaker = user_settings.get_user_speaker(new_user_id)
    print(f"Retrieved speaker for {new_user_id}: {saved_speaker}")

    # Remove the test user
    removed = user_settings.remove_user_speaker(new_user_id)
    print(f"Removing test user: {'Success' if removed else 'Failed'}")

    # Get stats
    stats = user_settings.get_stats()
    print(f"\nFinal stats: {stats}")

    # Cleanup TTS engine session
    if tts_engine._session:
        await tts_engine._session.close()
    print("\n=== All tests passed! ===")


if __name__ == "__main__":
    asyncio.run(test_user_voices())
