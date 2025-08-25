#!/usr/bin/env python3
"""Test script to create DiscordVoiceTTSBot instance."""

import asyncio

from src.discord_voice_bot.bot import DiscordVoiceTTSBot


class MockConfigManager:
    """Mock configuration manager for testing."""

    def get_intents(self):
        from discord import Intents

        return Intents.default()

    def get_command_prefix(self):
        return "!"

    def get_discord_token(self):
        return "mock_token"


async def test_bot_creation():
    """Test creating a bot instance."""
    try:
        config_manager = MockConfigManager()
        bot = DiscordVoiceTTSBot(config_manager)
        print("✅ Bot created successfully!")
        print(f"Bot type: {type(bot)}")
        print(f"Bot has http attribute: {hasattr(bot, 'http')}")
        if hasattr(bot, "http"):
            print(f"HTTP client type: {type(bot.http)}")
    except Exception as e:
        print(f"❌ Error creating bot: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_bot_creation())
