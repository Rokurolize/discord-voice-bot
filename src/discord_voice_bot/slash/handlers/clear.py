"""Clear slash command handler."""

import discord
from loguru import logger

from ...bot import DiscordVoiceTTSBot


async def handle(interaction: discord.Interaction, bot: DiscordVoiceTTSBot) -> None:
    """Handle clear slash command."""
    logger.debug("Handling /clear command from user id={} name={}", interaction.user.id, interaction.user.display_name)
    try:
        if not hasattr(bot, "voice_handler") or not bot.voice_handler:
            _ = await interaction.response.send_message("❌ Voice handler not available", ephemeral=True)
            return

        cleared_count = await bot.voice_handler.clear_all()
        _ = await interaction.response.send_message(f"🗑️ Cleared {cleared_count} messages from TTS queue", ephemeral=True)

    except Exception:
        logger.exception("Error in clear slash command")
        try:
            if interaction.response.is_done():
                _ = await interaction.followup.send("❌ Error clearing queue", ephemeral=True)
            else:
                _ = await interaction.response.send_message("❌ Error clearing queue", ephemeral=True)
        except Exception as followup_err:
            logger.debug(f"Suppressed secondary error while responding to interaction: {followup_err!s}")
