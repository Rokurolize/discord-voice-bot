#!/usr/bin/env python3
"""Force audio test by directly triggering bot's TTS functionality."""

import asyncio

from src.tts_engine import tts_engine


async def force_tts_test():
    """Force TTS test without Discord message dependency."""
    print("🧪 Force Testing TTS Audio...")

    # Get the global voice handler from the running bot
    # We'll simulate what should happen when `!tts test` is called

    test_text = "強制音声テストです！修正が動いているか確認中です。"

    # Create a mock voice client that would be connected
    class MockVoiceClient:
        def __init__(self):
            self.is_connected_value = True
            self.playing = False

        def is_connected(self):
            return self.is_connected_value

        def is_playing(self):
            return self.playing

        def play(self, audio_source, after=None):
            print(f"🎵 MockVoiceClient.play() called with {type(audio_source)}")
            print(f"🎵 Audio source: {audio_source}")

            # Simulate successful playback
            self.playing = True

            # Call the after callback with no error
            if after:

                def complete_playback():
                    self.playing = False
                    after(None)  # No error

                # Simulate playback completion after short delay
                asyncio.get_event_loop().call_later(1.0, complete_playback)

            return True

        def stop(self):
            self.playing = False
            print("🛑 MockVoiceClient.stop() called")

    # Test TTS and audio source creation
    await tts_engine.start()

    print(f"🎤 Testing TTS synthesis for: '{test_text}'")
    audio_source = await tts_engine.create_audio_source(test_text)

    if audio_source:
        print(f"✅ Audio source created: {type(audio_source)}")

        # Test the voice playback simulation
        mock_client = MockVoiceClient()

        print("🎵 Simulating voice client playback...")
        result = mock_client.play(audio_source)
        print(f"Play result: {result}")

        # Wait for simulated playback
        await asyncio.sleep(2)

        # Cleanup
        tts_engine.cleanup_audio_source(audio_source)
        print("🧹 Audio source cleaned up")

    else:
        print("❌ Failed to create audio source")

    await tts_engine.close()
    print("✅ Force TTS test completed!")


if __name__ == "__main__":
    asyncio.run(force_tts_test())
