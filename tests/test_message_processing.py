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


@pytest.mark.skip(reason="Discord integration test - requires valid bot token and server access")
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

        # Send a test message to the target channel
        test_message = await target_channel.send("🎤 テストメッセージ - ずんだもんが読み上げてね")
        assert test_message.content, "Failed to send test message"

        # Wait for message processing
        await asyncio.sleep(5)

        # Clean up the test message
        try:
            await test_message.delete()
        except Exception:
            pass  # Ignore cleanup errors

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
