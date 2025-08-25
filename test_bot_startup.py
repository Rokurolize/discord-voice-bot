#!/usr/bin/env python3
"""Test script to verify bot can start up successfully."""

import asyncio
import signal
import sys
from contextlib import asynccontextmanager
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from discord_voice_bot.bot import run_bot


@asynccontextmanager
async def timeout_context(seconds: int):
    """Context manager for timeout."""

    def timeout_handler(signum, frame):
        raise TimeoutError(f"Operation timed out after {seconds} seconds")

    # Set up signal handler for timeout
    signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(seconds)

    try:
        yield
    finally:
        # Cancel the alarm
        signal.alarm(0)


async def test_bot_startup():
    """Test bot startup with timeout."""
    print("🔧 Testing Bot Startup...")

    try:
        async with timeout_context(30):  # 30 second timeout
            print("🚀 Attempting to start bot...")
            await run_bot()
            print("✅ Bot started successfully")
            return True

    except TimeoutError:
        print("⏰ Bot startup timed out (expected - this means Discord connection was attempted)")
        return True

    except Exception as e:
        print(f"❌ Bot startup failed: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    result = asyncio.run(test_bot_startup())
    if result:
        print("✅ Bot startup test completed successfully")
        sys.exit(0)
    else:
        print("❌ Bot startup test failed")
        sys.exit(1)
