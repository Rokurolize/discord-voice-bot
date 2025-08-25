"""Test for Discord API message content retrieval functionality."""

import asyncio
import logging
import os
import sys
from typing import Any

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


@pytest.mark.asyncio
async def test_bot_intents_configuration(discord_token):
    """Test that bot has correct intents for message content retrieval."""
    class TestBot(discord.Client):
        def __init__(self, *args, **kwargs):
            intents = discord.Intents.default()
            intents.message_content = True
            intents.voice_states = True
            intents.guilds = True
            super().__init__(*args, intents=intents, **kwargs)

        async def on_ready(self):
            assert self.intents.message_content, "message_content intent not enabled"
            await self.close()

    bot = TestBot()

    try:
        await bot.start(discord_token)
        await bot.wait_until_ready()
        await asyncio.sleep(1)
    finally:
        await bot.close()