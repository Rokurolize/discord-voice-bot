#!/usr/bin/env python3
"""Simple test script that directly tests the self-message processing pipeline."""

import asyncio
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.discord_voice_bot.config_manager import ConfigManagerImpl
from src.discord_voice_bot.message_processor import MessageProcessor


class MockDiscordMessage:
    """Mock Discord message for testing."""

    def __init__(self, content, author_id, author_bot=False, channel_id=None):
        self.content = content
        self.author = MockAuthor(author_id, bot=author_bot)
        self.channel = MockChannel(channel_id or 1350964414286921749)  # Use target voice channel ID
        self.id = 12345
        self.type = MockMessageType()

    def __str__(self):
        return f"MockMessage(id={self.id}, author={self.author.name}, content='{self.content}')"


class MockAuthor:
    """Mock Discord author."""

    def __init__(self, user_id, bot=False):
        self.id = user_id
        self.bot = bot
        self.name = "TestBot" if bot else "TestUser"
        self.display_name = "TestBot" if bot else "TestUser"


class MockChannel:
    """Mock Discord channel."""

    def __init__(self, channel_id):
        self.id = channel_id


class MockMessageType:
    """Mock Discord message type."""

    def __init__(self):
        self.name = "default"


async def test_self_message_processing():
    """Test self-message processing pipeline directly."""
    print("🧪 Testing Self-Message Processing Pipeline")
    print("=" * 50)

    # Initialize components
    config_manager = ConfigManagerImpl()
    processor = MessageProcessor(config_manager)

    # Test bot user ID (same as self-message author)
    bot_user_id = 123456789

    print("✅ Configuration loaded:")
    print(f"   ENABLE_SELF_MESSAGE_PROCESSING = {config_manager.get_enable_self_message_processing()}")
    print(f"   Target Voice Channel ID = {config_manager.get_target_voice_channel_id()}")
    print(f"   Bot User ID = {bot_user_id}")

    # Test 1: Self-message should be processed
    print("\n📝 Test 1: Self-message processing")
    self_message = MockDiscordMessage("🎤 ボイス読み上げテスト: これは自動テストメッセージです。", bot_user_id, author_bot=True, channel_id=config_manager.get_target_voice_channel_id())

    print(f"   Message: {self_message}")

    should_process = await processor.should_process_message(self_message, bot_user_id)
    print(f"   should_process_message(): {should_process}")

    if should_process:
        processed_data = await processor.process_message(self_message, bot_user_id)
        print(f"   process_message() result: {processed_data is not None}")

        if processed_data:
            print("   Processed data:")
            print(f"     Text: {processed_data.get('text', 'N/A')}")
            print(f"     User ID: {processed_data.get('user_id', 'N/A')}")
            print(f"     Username: {processed_data.get('username', 'N/A')}")
            print(f"     Group ID: {processed_data.get('group_id', 'N/A')}")
            print(f"     Chunks: {len(processed_data.get('chunks', []))} chunks")

            for i, chunk in enumerate(processed_data.get("chunks", [])):
                print(f"       Chunk {i + 1}: '{chunk}'")
        else:
            print("   ❌ Processing returned None")
    else:
        print("   ❌ Self-message was rejected by should_process_message()")

    print("\n🎉 Pipeline testing completed!")


def main():
    """Main entry point."""
    try:
        print("🚀 Starting Self-Message Processing Pipeline Test")
        print("=" * 60)

        # Check if self-message processing is enabled
        config_manager = ConfigManagerImpl()
        if not config_manager.get_enable_self_message_processing():
            print("⚠️  WARNING: ENABLE_SELF_MESSAGE_PROCESSING is disabled!")
            print("   Self-messages will not be processed.")
            print("   Set ENABLE_SELF_MESSAGE_PROCESSING=true in your .env file")
            return

        # Run the test
        asyncio.run(test_self_message_processing())

    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
