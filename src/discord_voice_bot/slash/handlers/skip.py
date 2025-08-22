"""Skip slash command handler."""

import discord
from loguru import logger

from ...bot import DiscordVoiceTTSBot


async def handle(interaction: discord.Interaction, bot: DiscordVoiceTTSBot) -> None:
    """Handle skip slash command."""
    try:
        if not hasattr(bot, "voice_handler") or not bot.voice_handler:
            await interaction.response.send_message("❌ Voice handler not available", ephemeral=True)
            return

        skipped = await bot.voice_handler.skip_current()
        if skipped:
            await interaction.response.send_message("⏭️ Skipped current TTS message")
        else:
            await interaction.response.send_message("❌ No TTS message to skip", ephemeral=True)

    except Exception as e:
        logger.error(f"Error in skip slash command: {e}")
        await interaction.response.send_message("❌ Error skipping message", ephemeral=True)
