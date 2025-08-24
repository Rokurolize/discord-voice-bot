#!/usr/bin/env python3
"""Test script to verify self-message processing fix works correctly."""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.discord_voice_bot.config_manager import ConfigManagerImpl
from src.discord_voice_bot.message_processor import MessageProcessor


class MockDiscordMessage:
    """Mock Discord message for testing."""

    def __init__(self, content, author_id, author_bot=False, channel_id=1350964414286921749):
        self.content = content
        self.author = MockAuthor(author_id, bot=author_bot)
        self.channel = MockChannel(channel_id)
        self.id = 12345
        self.type = MockMessageType()


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
    """Test that self-messages are properly processed when enabled."""
    print("🧪 Testing Self-Message Processing Fix")
    print("=" * 50)

    # Initialize components
    config_manager = ConfigManagerImpl()
    processor = MessageProcessor(config_manager)

    # Test bot user ID (same as self-message author)
    bot_user_id = 12345

    print(f"✅ Configuration loaded: ENABLE_SELF_MESSAGE_PROCESSING = {config_manager.get_enable_self_message_processing()}")

    # Test 1: Self-message should be processed
    print("\n📝 Test 1: Self-message processing")
    self_message = MockDiscordMessage("Hello, I am the bot!", bot_user_id, author_bot=True)

    should_process = await processor.should_process_message(self_message, bot_user_id)
    print(f"   Self-message should_process: {should_process}")

    if should_process:
        processed_data = await processor.process_message(self_message, bot_user_id)
        print(f"   Processed data: {processed_data is not None}")
        if processed_data:
            print(f"   Text: {processed_data.get('text', 'N/A')}")
            print(f"   User ID: {processed_data.get('user_id', 'N/A')}")
    else:
        print("   ❌ Self-message was rejected")

    # Test 2: Regular user message should still work
    print("\n📝 Test 2: Regular user message processing")
    regular_message = MockDiscordMessage("Hello from user!", 99999, author_bot=False)

    should_process_regular = await processor.should_process_message(regular_message, bot_user_id)
    print(f"   Regular message should_process: {should_process_regular}")

    if should_process_regular:
        processed_data_regular = await processor.process_message(regular_message, bot_user_id)
        print(f"   Processed data: {processed_data_regular is not None}")

    # Test 3: Other bot message should be rejected
    print("\n📝 Test 3: Other bot message rejection")
    other_bot_message = MockDiscordMessage("Hello from another bot!", 54321, author_bot=True)

    should_process_other_bot = await processor.should_process_message(other_bot_message, bot_user_id)
    print(f"   Other bot message should_process: {should_process_other_bot}")

    print("\n🎉 Test completed!")


if __name__ == "__main__":
    asyncio.run(test_self_message_processing())
