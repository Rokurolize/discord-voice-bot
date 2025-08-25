#!/usr/bin/env python3
"""Test script to verify message processing pipeline works."""

import asyncio
import sys
from pathlib import Path
from unittest.mock import AsyncMock, Mock

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

import discord

from discord_voice_bot.config_manager import ConfigManagerImpl
from discord_voice_bot.event_message_handler import MessageHandler


async def test_message_pipeline():
    """Test message processing pipeline."""
    print("🔧 Testing Message Processing Pipeline...")

    config = ConfigManagerImpl()

    # Create a mock bot with required components
    bot = Mock()
    bot.user = Mock()
    bot.user.id = 123456789
    bot.stats = {"messages_processed": 0}

    # Mock voice handler
    voice_handler = Mock()
    voice_handler.add_to_queue = AsyncMock(return_value=None)
    voice_handler.rate_limiter = Mock()
    voice_handler.rate_limiter.wait_if_needed = AsyncMock(return_value=None)

    # Mock command handler
    command_handler = Mock()
    command_handler.process_command = AsyncMock(return_value=None)

    bot.voice_handler = voice_handler
    bot.command_handler = command_handler

    try:
        # Create message handler
        message_handler = MessageHandler(bot, config)

        # Create a mock Discord message
        message = Mock(spec=discord.Message)
        message.author = Mock()
        message.author.name = "TestUser"
        message.author.bot = False
        message.author.id = 987654321
        message.content = "こんにちは、テストメッセージです！"
        message.id = 12345
        message.channel = Mock()
        message.channel.id = 123456
        message.channel.name = "general"
        message.type = discord.MessageType.default
        message.created_at = discord.utils.utcnow()

        print(f"📝 Testing message: '{message.content}'")

        # Process the message
        await message_handler.handle_message(message)

        # Check if message was processed
        if voice_handler.add_to_queue.called:
            print("✅ Message was successfully added to TTS queue")
            call_args = voice_handler.add_to_queue.call_args[0][0]

            # Verify processed message structure
            if isinstance(call_args, dict):
                print("✅ Processed message has correct structure")
                expected_keys = ["content", "author_name", "channel_name", "message_id"]
                for key in expected_keys:
                    if key in call_args:
                        print(f"  - {key}: {call_args[key]}")
                    else:
                        print(f"  ❌ Missing key: {key}")
                        return False
                return True
            else:
                print("❌ Processed message is not a dictionary")
                return False
        else:
            print("❌ Message was not added to TTS queue")
            return False

    except Exception as e:
        print(f"❌ Message pipeline test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    _ = asyncio.run(test_message_pipeline())
