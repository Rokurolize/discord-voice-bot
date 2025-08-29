"""Voices embed creation for slash commands."""

import discord

from ...config import Config
from ...tts_engine import TTSEngine
from ...user_settings import UserSettings


async def create_voices_embed(user_id: str | int, config: Config, tts_engine: TTSEngine, user_settings: UserSettings) -> discord.Embed:
    """Create voices embed showing available speakers."""
    try:
        speakers = await tts_engine.get_available_speakers()

        # Get user's current setting (prefer ID to avoid name mismatches)
        user_id_str = str(user_id)
        current_speaker_id = user_settings.get_user_speaker(user_id_str, current_engine=config.tts_engine)
        current_speaker_name = None
        if current_speaker_id is not None:
            # Map ID back to a display name if available
            for name, sid in speakers.items():
                if sid == current_speaker_id:
                    current_speaker_name = name
                    break

        embed = discord.Embed(
            title=f"🎭 Available Voices ({config.tts_engine.upper()})",
            color=discord.Color.blue(),
            description="Use `/voice <name>` to set your personal voice",
        )

        # Group speakers by base name
        speaker_groups: dict[str, list[tuple[str, int]]] = {}
        for name, speaker_id in speakers.items():
            # Extract base name (e.g., "zunda" from "zunda_normal")
            base_name = name.split("_")[0] if "_" in name else name
            if base_name not in speaker_groups:
                speaker_groups[base_name] = []
            speaker_groups[base_name].append((name, speaker_id))

        # Add fields for each speaker group
        for base_name, variants in speaker_groups.items():
            field_lines: list[str] = []
            for name, speaker_id in variants:
                marker = "🔹" if current_speaker_id is not None and speaker_id == current_speaker_id else "▫️"
                field_lines.append(f"{marker} `{name}` ({speaker_id})")

            embed = embed.add_field(name=base_name.title(), value="\n".join(field_lines), inline=True)

        # Add current setting info
        if current_speaker_name:
            embed = embed.set_footer(text=f"Your current voice: {current_speaker_name}")
        else:
            embed = embed.set_footer(text="You're using the default voice")

        return embed

    except Exception:
        from loguru import logger

        logger.exception("Error creating voices embed")
        return discord.Embed(title="🎭 Available Voices", color=discord.Color.red(), description="❌ Error retrieving voice information")
