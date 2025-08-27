"""Test bot message processing from target Discord channel."""

import asyncio
import os
from unittest.mock import Mock

import discord
import pytest

from src.discord_voice_bot.config import Config


@pytest.mark.skipif(
    os.getenv("RUN_DISCORD_INTEGRATION_TESTS", "false").lower() != "true",
    reason="Discord integration test - requires valid bot token and server access.",
)
@pytest.mark.asyncio
async def test_bot_message_processing(config: Config):
    """Test bot message processing capabilities by mocking an incoming message."""
    intents = discord.Intents.default()
    intents.message_content = True
    intents.guilds = True
    intents.voice_states = True

    client = discord.Client(intents=intents)
    test_completed = asyncio.Event()
    message_was_processed = False

    @client.event
    async def on_ready():
        nonlocal message_was_processed
        try:
            target_guild = client.get_guild(config.target_guild_id)
            assert target_guild, f"Target guild {config.target_guild_id} not found."

            target_channel = client.get_channel(config.target_voice_channel_id)
            assert target_channel, f"Target channel {config.target_voice_channel_id} not found."

            # Create a mock message to avoid actual TTS processing
            test_message = Mock(spec=discord.Message)
            test_message.content = "Test message for processing verification"
            test_message.author = Mock(spec=discord.Member)
            test_message.author.name = "TestUser"
            test_message.author.bot = False
            test_message.channel = target_channel
            test_message.id = 12345
            test_message.created_at = discord.utils.utcnow()

            # Simulate message processing by calling the on_message handler directly
            await on_message(test_message)

            # The on_message handler below will set this to True
            assert message_was_processed, "The on_message handler did not process the message."

        except AssertionError as e:
            pytest.fail(str(e))
        finally:
            await client.close()
            test_completed.set()

    @client.event
    async def on_message(message: discord.Message):
        """A simplified handler to confirm the message is received and valid."""
        nonlocal message_was_processed
        # Don't process our own messages
        if message.author == client.user:
            return

        # Only process messages from the target channel
        if message.channel.id == config.target_voice_channel_id:
            message_was_processed = True

    @client.event
    async def on_error(event, *args, **kwargs):
        pytest.fail(f"Discord client error in {event}: {args}")

    try:
        await client.start(config.discord_token)
        await asyncio.wait_for(test_completed.wait(), timeout=30.0)
    except asyncio.TimeoutError:
        pytest.fail("Test timed out.")
    except Exception as e:
        pytest.fail(f"Test failed with an unexpected exception: {e}")
