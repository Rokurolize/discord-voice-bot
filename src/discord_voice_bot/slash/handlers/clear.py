"""Clear slash command handler."""

import discord
from loguru import logger

from ...bot import DiscordVoiceTTSBot


async def handle(interaction: discord.Interaction, bot: DiscordVoiceTTSBot) -> None:
    """Handle clear slash command."""
    logger.debug(f"Handling /clear command from user '{interaction.user}' (id={interaction.user.id})")
    try:
        if not hasattr(bot, "voice_handler") or not bot.voice_handler:
            _ = await interaction.response.send_message("❌ Voice handler not available", ephemeral=True)
            return

        cleared_count = await bot.voice_handler.clear_all()
        _ = await interaction.response.send_message(
            f"🗑️ Cleared {cleared_count} messages from TTS queue",
            ephemeral=True
        )

    except Exception:
        logger.exception("Error in clear slash command")
        _ = await interaction.response.send_message("❌ Error clearing queue", ephemeral=True)
