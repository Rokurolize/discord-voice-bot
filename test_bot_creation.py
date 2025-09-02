#!/usr/bin/env python3
"""Test script to create DiscordVoiceTTSBot instance."""

from typing import Any, cast

import pytest
from discord import Intents
from src.discord_voice_bot.bot import DiscordVoiceTTSBot
from src.discord_voice_bot.config import Config


@pytest.mark.asyncio
async def test_bot_creation(config: Config):
    """Test creating a bot instance."""
    bot = None
    try:
        # The bot now takes the config object directly
        bot = DiscordVoiceTTSBot(config=config)
        assert isinstance(bot, DiscordVoiceTTSBot)
        assert bot.config == config
        # Bot.command_prefix is a discord.py union type; cast for comparison
        assert cast(Any, bot).command_prefix == config.command_prefix
        assert isinstance(bot.intents, Intents)
        assert hasattr(bot, "http")
    finally:
        if bot:
            await bot.close()
