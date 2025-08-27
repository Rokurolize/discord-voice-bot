"""Voices slash command handler."""

import discord
from loguru import logger

from ...bot import DiscordVoiceTTSBot
from ..embeds.voices import create_voices_embed


async def handle(interaction: discord.Interaction, bot: DiscordVoiceTTSBot) -> None:
    """Handle voices slash command."""
    logger.debug("Handling /voices command from user id={} name={}", interaction.user.id, interaction.user.display_name)
    try:
        if not hasattr(bot, "tts_engine") or not hasattr(bot, "user_settings"):
            _ = await interaction.response.send_message("❌ Bot components not ready.", ephemeral=True)
            return

        embed = await create_voices_embed(
            user_id=interaction.user.id,
            config=bot.config,
            tts_engine=bot.tts_engine,
            user_settings=bot.user_settings,
        )
        _ = await interaction.response.send_message(embed=embed)

    except Exception:
        logger.exception("Error in voices slash command")
        _ = await interaction.response.send_message("❌ Error retrieving voices", ephemeral=True)
