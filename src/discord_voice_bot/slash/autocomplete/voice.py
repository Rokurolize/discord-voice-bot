"""Voice autocomplete handler."""

import discord
from discord import app_commands
from loguru import logger

from ...config import Config


async def voice_autocomplete(interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
    """
    Return autocomplete choices for selecting a voice.

    Reads the available speakers from the environment configuration (uses Config.from_env(), looks up the configured TTS engine key from `config.tts_engine` or `"voicevox"`, then reads `config.engines[engine_key]["speakers"]`) and returns up to 25 app_commands.Choice entries whose names contain the user's current input (case-insensitive).

    Args:
        interaction: The command interaction context.
        current: The user's current input to match against speaker names.

    Returns:
        list[app_commands.Choice[str]]: Matching choices (max 25). On error, an empty list is returned.

    """
    try:
        # Lightweight path: read speakers from static config mapping
        config = Config.from_env()
        engine_key = (config.tts_engine or "voicevox").lower()
        engine_cfg = config.engines.get(engine_key, {})
        speakers = engine_cfg.get("speakers", {}) or {}

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
