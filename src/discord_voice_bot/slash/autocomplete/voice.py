"""Voice autocomplete handler."""

import discord
from discord import app_commands
from loguru import logger

from ...config import Config
from ...tts_engine import get_tts_engine


async def voice_autocomplete(interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
    """Provide autocomplete suggestions for voice selection."""
    try:
        # Create TTS engine instance for autocomplete using current environment config
        config = Config.from_env()
        tts_engine = await get_tts_engine(config)
        speakers = await tts_engine.get_available_speakers()

        # Filter speakers based on current input
        choices: list[app_commands.Choice[str]] = []
        current_lower = current.lower()

        for name in speakers.keys():
            if current_lower in name.lower():
                choices.append(app_commands.Choice(name=name, value=name))
                if len(choices) >= 25:  # Discord's limit for autocomplete choices
                    break

        return choices

    except Exception as e:
        logger.error(f"Error in voice autocomplete: {e}")
        return []
