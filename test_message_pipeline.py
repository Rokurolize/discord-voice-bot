#!/usr/bin/env python3
"""Test script to verify message processing pipeline works."""

from unittest.mock import AsyncMock, Mock

import discord
import pytest

from discord_voice_bot.config import Config
from discord_voice_bot.event_message_handler import MessageHandler


@pytest.mark.asyncio
async def test_message_pipeline(config: Config):
    """Test message processing pipeline."""
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
    message.channel.id = config.target_voice_channel_id  # Use the ID from the config
    message.channel.name = "general"
    message.type = discord.MessageType.default
    message.created_at = discord.utils.utcnow()

    # Process the message
    await message_handler.handle_message(message)

    # Check if message was processed and added to the queue
    voice_handler.add_to_queue.assert_called_once()
    call_args = voice_handler.add_to_queue.call_args[0][0]

    # Verify processed message structure
    assert isinstance(call_args, dict)
    expected_keys = ["content", "author_name", "channel_name", "message_id"]
    for key in expected_keys:
        assert key in call_args
        assert call_args[key] is not None

    assert call_args["content"] == message.content
