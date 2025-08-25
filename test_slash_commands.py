#!/usr/bin/env python3
"""Test script to verify slash command registration works."""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

import discord
from discord.ext import commands
from loguru import logger

from discord_voice_bot.config_manager import ConfigManagerImpl
from discord_voice_bot.slash.registry import SlashCommandRegistry


async def test_slash_commands():
    """Test slash command registration."""
    print("🔧 Testing Slash Command Registration...")

    config = ConfigManagerImpl()

    # Create a minimal bot instance
    intents = discord.Intents.default()
    intents.message_content = True
    intents.voice_states = True

    bot = commands.Bot(command_prefix="!", intents=intents)

    try:
        # Create slash command registry
        registry = SlashCommandRegistry(bot)

        # Register slash commands (without syncing to avoid auth requirements)
        logger.info("🔧 Registering slash commands...")

        # Clear existing commands to avoid conflicts
        bot.tree.clear_commands(guild=None)

        # Register core commands
        await registry._register_core()

        # Register voice commands
        await registry._register_voice()

        # Register utility commands
        await registry._register_util()

        # Get registered commands
        registered = registry.get_registered_commands()
        print(f"✅ Successfully registered {len(registered)} slash commands:")

        for name, info in registered.items():
            print(f"  - /{name}: {info.get('handler', 'No handler')}")

        # Test that we have the expected commands
        expected_commands = ["status", "skip", "clear", "voice", "voices", "voicecheck", "reconnect", "test"]

        missing_commands = []
        for cmd in expected_commands:
            if cmd not in registered:
                missing_commands.append(cmd)

        if missing_commands:
            print(f"❌ Missing expected commands: {missing_commands}")
            return False
        else:
            print("✅ All expected commands are registered")
            return True

    except Exception as e:
        print(f"❌ Slash command registration test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    _ = asyncio.run(test_slash_commands())
