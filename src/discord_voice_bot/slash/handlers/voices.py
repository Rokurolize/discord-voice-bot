"""Voices slash command handler."""

import discord
from loguru import logger

from ...bot import DiscordVoiceTTSBot
from ..embeds.voices import create_voices_embed


async def handle(interaction: discord.Interaction, bot: DiscordVoiceTTSBot) -> None:
    """Handle voices slash command."""
    try:
        embed = await create_voices_embed()
        await interaction.response.send_message(embed=embed)

    except Exception as e:
        logger.error(f"Error in voices slash command: {e}")
        await interaction.response.send_message("❌ Error retrieving voices", ephemeral=True)
