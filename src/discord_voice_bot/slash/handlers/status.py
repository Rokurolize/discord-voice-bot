"""Status slash command handler."""

import discord
from loguru import logger

from ...bot import DiscordVoiceTTSBot
from ..embeds.status import create_basic_status_embed, create_status_embed


async def handle(interaction: discord.Interaction, bot: DiscordVoiceTTSBot) -> None:
    """Handle status slash command."""
    logger.debug("Handling /status command from user='{}' (id={})", interaction.user, interaction.user.id)
    try:
        if hasattr(bot, "status_manager") and bot.status_manager:
            status = bot.status_manager.get_statistics()
            embed = await create_status_embed(status, bot.config)
        else:
            # Fallback to basic status
            embed = await create_basic_status_embed()

        _ = await interaction.response.send_message(embed=embed)

    except Exception:
        logger.exception("Error in status slash command")
        try:
            if interaction.response.is_done():
                _ = await interaction.followup.send("❌ Error retrieving status", ephemeral=True)
            else:
                _ = await interaction.response.send_message("❌ Error retrieving status", ephemeral=True)
        except Exception as followup_err:
            logger.debug(f"Suppressed secondary error while responding to interaction: {followup_err!s}")
