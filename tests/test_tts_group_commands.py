import discord
import pytest
from discord.ext import commands

from discord_voice_bot.cogs.voice_group import TTSGroup


async def _collect_commands(bot: commands.Bot) -> set[str]:
    cmds = bot.tree.get_commands()
    return {c.name for c in cmds}


@pytest.mark.asyncio
async def test_tts_group_registration() -> None:
    intents = discord.Intents.none()
    bot = commands.Bot(command_prefix="!", intents=intents)

    # Register the group cog
    await bot.add_cog(TTSGroup(bot))

    # Inspect CommandTree for the /tts group
    registered = await _collect_commands(bot)

    assert "tts" in registered
