#!/usr/bin/env python3
"""Discord Voice TTS Bot - Main Entry Point."""

import asyncio

from .bot_factory import BotFactory


async def run_bot() -> None:
    """Create and run the Discord bot."""
    try:
        factory = BotFactory()
        bot = await factory.create_bot()
        await bot.start_with_config()
    except Exception as e:
        print(f"Failed to start bot: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(run_bot())
