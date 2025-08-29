"""Voices slash command handler."""

import inspect

import discord
from loguru import logger

from ...bot import DiscordVoiceTTSBot
from ..embeds.voices import create_voices_embed


async def handle(interaction: discord.Interaction, bot: DiscordVoiceTTSBot) -> None:
    """Handle voices slash command."""
    logger.debug("Handling /voices command from user id={} name={}", interaction.user.id, interaction.user.display_name)
    created_ephemeral: bool = False
    tts_engine = None
    try:
        # Prefer long-lived engine attached to bot to avoid repeated startups
        from ...tts_engine import get_tts_engine
        from ...user_settings import load_user_settings

        tts_engine = getattr(bot, "tts_engine", None)
        if tts_engine is None:
            tts_engine = await get_tts_engine(bot.config)
            created_ephemeral = True
        user_settings = load_user_settings()

        embed = await create_voices_embed(
            user_id=interaction.user.id,
            config=bot.config,
            tts_engine=tts_engine,
            user_settings=user_settings,
        )
        _ = await interaction.response.send_message(embed=embed)

    except Exception:
        logger.exception("Error in voices slash command")
        if interaction.response.is_done():
            _ = await interaction.followup.send("❌ Error retrieving voices", ephemeral=True)
        else:
            _ = await interaction.response.send_message("❌ Error retrieving voices", ephemeral=True)
    finally:
        # If we created a one-off engine instance, close it to avoid leaks
        if created_ephemeral and tts_engine is not None:
            try:
                close = getattr(tts_engine, "close", None)
                if callable(close):
                    res = close()
                    if inspect.isawaitable(res):
                        await res
            except Exception:
                pass
