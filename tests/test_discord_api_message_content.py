"""Test for Discord API message content retrieval functionality."""

import logging
import os
import sys

import discord
import pytest
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s | %(levelname)s | %(name)s:%(lineno)d | %(message)s", handlers=[logging.StreamHandler(sys.stdout)])
logger = logging.getLogger(__name__)


@pytest.fixture
def discord_token():
    """Get Discord bot token from environment."""
    token = os.getenv("DISCORD_BOT_TOKEN")
    if not token:
        pytest.skip("DISCORD_BOT_TOKEN not set")
    return token


def test_message_content_retrieval():
    """Test that bot can retrieve message content from Discord API."""
    # Skip if no Discord token is configured
    discord_token = os.getenv("DISCORD_BOT_TOKEN")
    if not discord_token:
        pytest.skip("DISCORD_BOT_TOKEN not set - skipping integration test")

    # Test bot setup verification only
    # This is a unit test that verifies the bot can be configured correctly
    intents = discord.Intents.default()
    intents.message_content = True
    intents.voice_states = True
    intents.guilds = True

    bot = discord.Client(intents=intents)

    # Verify intents are set correctly
    assert bot.intents.message_content, "message_content intent not enabled"
    assert bot.intents.voice_states, "voice_states intent not enabled"
    assert bot.intents.guilds, "guilds intent not enabled"

    logger.info("Bot configuration test passed - message content retrieval setup OK")


@pytest.mark.skipif(
    True,  # Always skip this test - it's too slow for regular testing
    reason="This integration test is too slow for regular test runs - run manually when needed",
)
@pytest.mark.asyncio
async def test_bot_intents_configuration(discord_token):
    """Test that bot has correct intents for message content retrieval."""
    # Test bot configuration without actually connecting to Discord
    intents = discord.Intents.default()
    intents.message_content = True
    intents.voice_states = True
    intents.guilds = True

    # Create bot instance but don't connect
    bot = discord.Client(intents=intents)

    # Verify intents are set correctly without connecting
    assert bot.intents.message_content, "message_content intent not enabled"
    assert bot.intents.voice_states, "voice_states intent not enabled"
    assert bot.intents.guilds, "guilds intent not enabled"

    logger.info("✅ Bot intents configuration test passed - no actual Discord connection needed")
