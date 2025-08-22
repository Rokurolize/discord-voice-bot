"""Clear slash command handler."""

import discord
from loguru import logger

from ...bot import DiscordVoiceTTSBot


async def handle(interaction: discord.Interaction, bot: DiscordVoiceTTSBot) -> None:
    """Handle clear slash command."""
    try:
        if not hasattr(bot, "voice_handler") or not bot.voice_handler:
            await interaction.response.send_message("❌ Voice handler not available", ephemeral=True)
            return

        cleared_count = await bot.voice_handler.clear_all()
        await interaction.response.send_message(f"🗑️ Cleared {cleared_count} messages from TTS queue")

    except Exception as e:
        logger.error(f"Error in clear slash command: {e}")
        await interaction.response.send_message("❌ Error clearing queue", ephemeral=True)
