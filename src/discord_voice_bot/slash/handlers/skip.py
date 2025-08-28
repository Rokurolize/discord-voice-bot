"""Skip slash command handler."""

import discord
from loguru import logger

from ...bot import DiscordVoiceTTSBot


async def handle(interaction: discord.Interaction, bot: DiscordVoiceTTSBot) -> None:
    """Handle skip slash command."""
    logger.debug("Handling /skip command from user id={} name={}", interaction.user.id, interaction.user.display_name)
    try:
        if not hasattr(bot, "voice_handler") or not bot.voice_handler:
            _ = await interaction.response.send_message("❌ Voice handler not available", ephemeral=True)
            return

        skipped = await bot.voice_handler.skip_current()
        if skipped:
            _ = await interaction.response.send_message("⏭️ Skipped current TTS message", ephemeral=True)
        else:
            _ = await interaction.response.send_message("❌ No TTS message to skip", ephemeral=True)

    except Exception:
        logger.exception("Error in skip slash command")
        try:
            if interaction.response.is_done():
                _ = await interaction.followup.send("❌ Error skipping message", ephemeral=True)
            else:
                _ = await interaction.response.send_message("❌ Error skipping message", ephemeral=True)
        except Exception as followup_err:
            logger.debug(f"Suppressed secondary error while responding to interaction: {followup_err!s}")
