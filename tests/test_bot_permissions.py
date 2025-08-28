#!/usr/bin/env python3
"""Test script to verify bot permissions and connectivity to target Discord server/channel."""
import asyncio
import logging
import os

import discord
import pytest

from discord_voice_bot.config import Config

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
    intents.members = True

    client = discord.Client(intents=intents)
    test_completed = asyncio.Event()

    @client.event
    async def on_ready():
        try:
            logger.info(f"Bot connected as: {client.user}")
            assert len(client.guilds) > 0, "Bot is not in any guilds."

            target_guild = client.get_guild(config.target_guild_id)
            assert target_guild, f"Target guild {config.target_guild_id} not found!"
            logger.info(f"Found target guild: {target_guild.name}")

            bot_member = await target_guild.fetch_member(client.user.id)
            assert bot_member, "Bot is not a member of the target guild!"

            target_channel = client.get_channel(config.target_voice_channel_id)
            assert target_channel, f"Target channel {config.target_voice_channel_id} not found!"
            assert isinstance(
                target_channel, discord.VoiceChannel
            ), "Target channel is not a voice channel."

            chan_perms = target_channel.permissions_for(bot_member)
            assert chan_perms.connect, "Bot is missing 'connect' permission on the target channel."
            assert chan_perms.speak, "Bot is missing 'speak' permission on the target channel."
            logger.info(f"Bot has required voice permissions on: {target_channel.name}")

        except AssertionError as e:
            pytest.fail(str(e))
        finally:
            await client.close()
            test_completed.set()

    @client.event
    async def on_error(event, *args, **kwargs):
        try:
            await client.close()
        finally:
            pytest.fail(f"Discord client error in {event}: {args}")

    try:
        await client.start(config.discord_token)
        await asyncio.wait_for(test_completed.wait(), timeout=30.0)
    except TimeoutError:
        pytest.fail("Test timed out.")
    except Exception as e:
        pytest.fail(f"Test failed with an unexpected exception: {e}")
