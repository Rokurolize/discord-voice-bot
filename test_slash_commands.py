#!/usr/bin/env python3
"""Test script to verify slash command registration works."""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

import discord
from discord.ext import commands

from discord_voice_bot.cogs.status import StatusCommands
from discord_voice_bot.cogs.voice import VoiceCommands


async def test_slash_commands():
    """Test slash command registration."""
    print("🔧 Testing Slash Command Registration...")

    # Create a minimal bot instance
    intents = discord.Intents.default()
    intents.message_content = True
    intents.voice_states = True

    bot = commands.Bot(command_prefix="!", intents=intents)

    try:
        # Clear existing commands to avoid conflicts and load Hybrid Cogs
        bot.tree.clear_commands(guild=None)
        await bot.add_cog(StatusCommands(bot))
        await bot.add_cog(VoiceCommands(bot))

        # Inspect CommandTree for registered commands
        commands_list = bot.tree.get_commands()
        registered = {cmd.name for cmd in commands_list}
        print(f"✅ Successfully registered {len(registered)} slash commands:")
        for name in sorted(registered):
            print(f"  - /{name}")

        # Test that we have the expected commands
        expected_commands = ["status", "skip", "clear", "voice", "voices", "voicecheck", "reconnect", "test"]

        missing_commands: list[str] = []
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
