#!/usr/bin/env python3
"""Test script to create DiscordVoiceTTSBot instance."""

import asyncio

from src.discord_voice_bot.bot import DiscordVoiceTTSBot


async def test_bot_creation():
    """Test creating a bot instance."""
    try:
        bot = DiscordVoiceTTSBot()
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
