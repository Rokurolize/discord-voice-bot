#!/usr/bin/env python3
"""Test script to create DiscordVoiceTTSBot instance."""

import pytest
from discord import Intents

from src.discord_voice_bot.bot import DiscordVoiceTTSBot
from src.discord_voice_bot.config import Config


@pytest.mark.asyncio
async def test_bot_creation(config: Config):
    """Test creating a bot instance."""
    try:
        # The bot now takes the config object directly
        bot = DiscordVoiceTTSBot(config=config)
        assert isinstance(bot, DiscordVoiceTTSBot)
        assert bot.config == config
        assert bot.command_prefix == config.command_prefix
        assert isinstance(bot.intents, Intents)
        assert hasattr(bot, "http")

    except Exception as e:
        pytest.fail(f"Error creating bot: {e}")
