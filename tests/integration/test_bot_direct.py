#!/usr/bin/env python3
"""Direct test of bot functionality without Discord API."""

import asyncio

from src.config import config
from src.message_processor import message_processor
from src.tts_engine import tts_engine


class MockMessage:
    """Mock Discord message for testing."""

    def __init__(self, content, author_name="TestUser", channel_id=None):
        self.content = content
        self.channel = MockChannel(channel_id or config.target_voice_channel_id)
        self.author = MockAuthor(author_name)
        self.type = MockMessageType()


class MockChannel:
    def __init__(self, channel_id):
        self.id = channel_id


class MockAuthor:
    def __init__(self, name):
        self.display_name = name
        self.name = name
        self.id = 12345
        self.bot = False


class MockMessageType:
    @property
    def name(self):
        return "default"


async def test_message_processing():
    """Test message processing and TTS synthesis."""
    print("🧪 Testing Message Processing and TTS...")

    # Start TTS engine
    await tts_engine.start()

    test_messages = [
        ("こんにちは、ずんだもんなのだ！", "TestUser1"),
        ("Hello, this is an English test!", "TestUser2"),
        ("日本語とEnglish混合テスト", "TestUser3"),
        ("絵文字テスト😊🎉", "TestUser4"),
        ("短い", "TestUser5"),
    ]

    for i, (content, user) in enumerate(test_messages, 1):
        print(f"\n--- Test Message {i} ---")
        print(f'Original: "{content}" from {user}')

        # Create mock message
        mock_msg = MockMessage(content, user)

        # Test message processing
        should_process = await message_processor.should_process_message(mock_msg)
        print(f"Should process: {should_process}")

        if should_process:
            # Test TTS message creation
            tts_text = await message_processor.create_tts_message(mock_msg)
            print(f'TTS text: "{tts_text}"')

            if tts_text:
                # Test TTS synthesis
                audio_data = await tts_engine.synthesize_audio(tts_text)
                if audio_data:
                    print(f"✅ TTS synthesis successful: {len(audio_data)} bytes")
                else:
                    print("❌ TTS synthesis failed")
            else:
                print("❌ No TTS text generated")
        else:
            print("⏭️ Message skipped (filtered)")

    await tts_engine.close()
    print("\n✅ Message processing tests completed!")


if __name__ == "__main__":
    asyncio.run(test_message_processing())
