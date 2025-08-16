#!/usr/bin/env python3
"""Direct audio test - bypassing Discord message processing."""

import asyncio

from src.tts_engine import tts_engine
from src.voice_handler import VoiceHandler


class MockBot:
    """Mock Discord client for testing."""

    def __init__(self):
        self.user = type("User", (), {"id": 12345})()


async def test_audio_pipeline():
    """Test the complete audio pipeline."""
    print("🧪 Testing Audio Pipeline Directly...")

    # Test TTS synthesis
    print("\n--- Step 1: TTS Synthesis ---")
    await tts_engine.start()

    test_text = "音声テスト、こんにちはなのだ！"
    audio_data = await tts_engine.synthesize_audio(test_text)

    if audio_data:
        print(f"✅ TTS synthesis successful: {len(audio_data)} bytes")
    else:
        print("❌ TTS synthesis failed")
        return

    # Test Discord audio source creation
    print("\n--- Step 2: Discord Audio Source Creation ---")
    audio_source = await tts_engine.create_audio_source(test_text)

    if audio_source:
        print("✅ Discord audio source created successfully")
        print(f"Audio source type: {type(audio_source)}")

        # Check if temp file exists
        if hasattr(audio_source, "_temp_path"):
            import os

            temp_exists = os.path.exists(audio_source._temp_path)
            print(f"Temp file exists: {temp_exists} ({audio_source._temp_path})")

        # Clean up
        tts_engine.cleanup_audio_source(audio_source)

    else:
        print("❌ Discord audio source creation failed")
        return

    # Test voice handler queue
    print("\n--- Step 3: Voice Handler Queue Test ---")
    mock_bot = MockBot()
    voice_handler = VoiceHandler(mock_bot)

    success = await voice_handler.add_to_queue(test_text, "TestUser")
    if success:
        print("✅ Successfully added to voice queue")
        print(f"Queue status: {voice_handler.get_queue_status()}")
    else:
        print("❌ Failed to add to voice queue")

    await tts_engine.close()
    print("\n✅ Direct audio pipeline test completed!")


if __name__ == "__main__":
    asyncio.run(test_audio_pipeline())
