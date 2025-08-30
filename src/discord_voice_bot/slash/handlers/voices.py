"""Voices slash command handler."""

import asyncio

import discord
from loguru import logger

from ...bot import DiscordVoiceTTSBot
from ..embeds.voices import create_voices_embed


async def handle(interaction: discord.Interaction, bot: DiscordVoiceTTSBot) -> None:
    """Handle voices slash command."""
    logger.debug("Handling /voices command from user id={} name={}", interaction.user.id, interaction.user.display_name)
    tts_engine = None
    try:
        # Prefer long-lived engine attached to bot to avoid repeated startups
        from ...tts_engine import get_tts_engine
        from ...user_settings import load_user_settings

        # Always use cached/shared engine; attach to bot if not present
        tts_engine = await get_tts_engine(bot.config)
        user_settings = load_user_settings()

        embed = await create_voices_embed(
            user_id=interaction.user.id,
            config=bot.config,
            tts_engine=tts_engine,
            user_settings=user_settings,
        )
        _ = await interaction.response.send_message(embed=embed)

    except asyncio.CancelledError:
        # Propagate cancellations for proper task handling (timeouts, etc.)
        raise
    except Exception:
        logger.exception("Error in voices slash command")
        if interaction.response.is_done():
            _ = await interaction.followup.send("❌ Error retrieving voices", ephemeral=True)
        else:
            _ = await interaction.response.send_message("❌ Error retrieving voices", ephemeral=True)
    finally:
        # Shared engine is cache-managed; do not close here
        pass
