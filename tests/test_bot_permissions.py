#!/usr/bin/env python3
"""Test script to verify bot permissions and connectivity to target Discord server/channel."""
import logging
import os

import discord
import pytest

from src.discord_voice_bot.config import Config

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@pytest.mark.skipif(
    os.getenv("RUN_DISCORD_INTEGRATION_TESTS", "false").lower() != "true",
    reason="This is a slow integration test that requires a live Discord bot token and server.",
)
@pytest.mark.asyncio
async def test_bot_permissions(config: Config):
    """Test bot permissions and connectivity."""
    intents = discord.Intents.default()
    intents.guilds = True
    intents.voice_states = True

    client = discord.Client(intents=intents)
    test_completed = asyncio.Event()

    @client.event
    async def on_ready():
        try:
            logger.info(f"Bot connected as: {client.user}")
            assert len(client.guilds) > 0, "Bot is not in any guilds."

            # Find target guild
            target_guild = client.get_guild(config.target_guild_id)
            assert target_guild, f"Target guild {config.target_guild_id} not found!"
            logger.info(f"Found target guild: {target_guild.name}")

            # Check bot's permissions in the guild
            bot_member = target_guild.get_member(client.user.id)
            assert bot_member, "Bot is not a member of the target guild!"

            # Check voice permissions
            voice_permissions = bot_member.guild_permissions
            assert voice_permissions.connect, "Bot is missing 'connect' permission."
            assert voice_permissions.speak, "Bot is missing 'speak' permission."
            logger.info("Bot has required voice permissions.")

            # Find target voice channel
            target_channel = client.get_channel(config.target_voice_channel_id)
            assert target_channel, f"Target channel {config.target_voice_channel_id} not found!"
            assert isinstance(
                target_channel, discord.VoiceChannel
            ), "Target channel is not a voice channel."
            logger.info(f"Found target voice channel: {target_channel.name}")

        except AssertionError as e:
            pytest.fail(str(e))
        finally:
            await client.close()
            test_completed.set()

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
