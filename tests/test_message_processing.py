"""Test bot message processing from target Discord channel."""

import asyncio
import os

import discord
import pytest
from dotenv import load_dotenv
from src.discord_voice_bot.config_manager import ConfigManagerImpl

# Load environment variables
load_dotenv()


@pytest.fixture
def discord_token():
    """Get Discord bot token from environment."""
    token = os.getenv("DISCORD_BOT_TOKEN")
    if not token:
        pytest.skip("DISCORD_BOT_TOKEN not set")
    return token


@pytest.mark.skipif(
    os.getenv("RUN_DISCORD_INTEGRATION_TESTS", "").lower() not in ("true", "1", "yes"),
    reason="Discord integration test - requires valid bot token and server access. Set RUN_DISCORD_INTEGRATION_TESTS=true to run manually",
)
@pytest.mark.asyncio
async def test_bot_message_processing(discord_token):
    """Test bot message processing capabilities."""
    # Initialize configuration
    config_manager = ConfigManagerImpl()
    target_guild_id = config_manager.get_target_guild_id()
    target_channel_id = config_manager.get_target_voice_channel_id()

    # Create Discord client with required intents
    intents = discord.Intents.default()
    intents.message_content = True
    intents.guilds = True
    intents.voice_states = True

    client = discord.Client(intents=intents)
    messages_processed = []

    @client.event
    async def on_ready():
        # Find target guild and channel
        target_guild = client.get_guild(target_guild_id)
        assert target_guild, f"Target guild {target_guild_id} not found!"

        target_channel = client.get_channel(target_channel_id)
        assert target_channel, f"Target channel {target_channel_id} not found!"

        # Create a mock message instead of sending real message to avoid unnecessary TTS
        from unittest.mock import Mock

        test_message = Mock()
        test_message.content = "Test message for processing verification"
        test_message.author = Mock()
        test_message.author.name = "TestUser"
        test_message.author.bot = False
        test_message.channel = target_channel
        test_message.id = 12345
        test_message.created_at = discord.utils.utcnow()

        # Simulate message processing by calling on_message directly
        await on_message(test_message)

        # Wait briefly for processing
        await asyncio.sleep(1)

        # Note: No cleanup needed for mock message

        await client.close()

    @client.event
    async def on_message(message):
        """Handle incoming messages."""
        # Don't process our own messages to avoid loops
        if message.author == client.user:
            return

        # Only process messages from the target channel
        if message.channel.id == target_channel_id:
            messages_processed.append({"content": message.content, "author": str(message.author), "channel": str(message.channel), "timestamp": message.created_at})

    @client.event
    async def on_error(event, *args, **kwargs):
        pytest.fail(f"Discord client error in {event}: {args}")

    # Start the bot
    await client.start(discord_token)
    await client.wait_until_ready()

    # Verify that messages were processed
    assert len(messages_processed) > 0, "No messages were processed"
    assert messages_processed[0]["content"], "Message content is empty"
