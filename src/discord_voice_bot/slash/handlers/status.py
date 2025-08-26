"""Status slash command handler."""

import discord
from loguru import logger

from ...bot import DiscordVoiceTTSBot
from ..embeds.status import create_basic_status_embed, create_status_embed


async def handle(interaction: discord.Interaction, bot: DiscordVoiceTTSBot) -> None:
    """Handle status slash command."""
    logger.debug(f"Handling /status command from user '{interaction.user.name}'")
    try:
        if hasattr(bot, "status_manager") and bot.status_manager:
            status = bot.status_manager.get_statistics()
            embed = await create_status_embed(status)
        else:
            # Fallback to basic status
            embed = await create_basic_status_embed()

        _ = await interaction.response.send_message(embed=embed)

    except Exception as e:
        logger.error(f"Error in status slash command: {e}")
        _ = await interaction.response.send_message("❌ Error retrieving status", ephemeral=True)
