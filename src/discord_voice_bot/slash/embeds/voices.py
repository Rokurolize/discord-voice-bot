"""Voices embed creation for slash commands."""

import discord

from ...config import Config
from ...tts_engine import TTSEngine
from ...user_settings import UserSettings


async def create_voices_embed(user_id: str | int, config: Config, tts_engine: TTSEngine, user_settings: UserSettings) -> discord.Embed:
    """
    Build a Discord Embed listing available TTS voices and highlighting the user's current selection.

    This coroutine fetches available speakers from the provided TTS engine, groups them by base name (the segment before the first underscore, e.g., "zunda" from "zunda_normal"), and adds one embed field per group with each variant listed. The user's current speaker is resolved by looking up their speaker ID via user_settings for the configured engine; the current variant is highlighted by marker and, when available, shown in the embed footer. If an error occurs while building the embed, a red error embed is returned indicating voice information could not be retrieved.

    Args:
        user_id: Discord user identifier used to resolve the user's current speaker (stringified internally).
        config: Resolved configuration, including the active TTS engine name.
        tts_engine: Engine used to retrieve available speakers.
        user_settings: Store for per-user voice selections.

    Returns:
        discord.Embed: Populated embed of voices, or an error embed on failure.

    """
    try:
        speakers = tts_engine.get_available_speakers()

        # Get user's current setting (prefer ID to avoid name mismatches)
        user_id_str = str(user_id)
        current_speaker_id = user_settings.get_user_speaker(user_id_str, current_engine=config.tts_engine)
        current_speaker_name = None
        if current_speaker_id is not None:
            # O(1) reverse lookup for current speaker name
            name_by_id = {sid: name for name, sid in speakers.items()}
            current_speaker_name = name_by_id.get(current_speaker_id)

        embed = discord.Embed(
            title=f"🎭 Available Voices ({config.tts_engine.upper()})",
            color=discord.Color.blue(),
            description="Use `/voice <name>` to set your personal voice",
        )

        # Group speakers by base name
        speaker_groups: dict[str, list[tuple[str, int]]] = {}
        for name, speaker_id in speakers.items():
            # Extract base name (e.g., "zunda" from "zunda_normal")
            base_name = name.split("_", 1)[0]
            if base_name not in speaker_groups:
                speaker_groups[base_name] = []
            speaker_groups[base_name].append((name, speaker_id))

        # Add fields for each speaker group in deterministic order
        # Discord limits: max 25 fields total, 1024 chars per field value
        MAX_FIELDS = 25
        MAX_FIELD_CHARS = 1024
        fields_added = 0
        groups_shown = 0

        for base_name in sorted(speaker_groups):
            if fields_added >= MAX_FIELDS:
                break

            variants = sorted(speaker_groups[base_name], key=lambda x: x[0])
            field_lines: list[str] = []
            group_field_added = False
            for name, speaker_id in variants:
                marker = "🔹" if speaker_id == current_speaker_id else "▫️"
                line = f"{marker} `{name}` ({speaker_id})"
                # Ensure we don't exceed per-field character limits; flush if needed
                prospective = ("\n".join(field_lines + [line])) if field_lines else line
                if len(prospective) > MAX_FIELD_CHARS:
                    if field_lines:
                        _ = embed.add_field(name=base_name.title(), value="\n".join(field_lines), inline=True)
                        fields_added += 1
                        if not group_field_added:
                            groups_shown += 1
                            group_field_added = True
                        if fields_added >= MAX_FIELDS:
                            break
                        field_lines = []
                        # If a single line is too long (unlikely), truncate safely
                        if len(line) > MAX_FIELD_CHARS:
                            line = line[: MAX_FIELD_CHARS - 1] + "…"
                field_lines.append(line)

            if fields_added < MAX_FIELDS and field_lines:
                _ = embed.add_field(name=base_name.title(), value="\n".join(field_lines), inline=True)
                fields_added += 1
                if not group_field_added:
                    groups_shown += 1
                    group_field_added = True

        # If we had to cap fields, add a summary note (count groups, not fields)
        total_groups = len(speaker_groups)
        if fields_added >= MAX_FIELDS and total_groups > groups_shown:
            remaining = max(0, total_groups - groups_shown)
            summary = f"…and {remaining} more group(s) not shown to fit Discord limits."
            if embed.description:
                embed.description += f"\n{summary}"
            else:
                embed.description = summary

        # Add current setting info
        if current_speaker_name:
            _ = embed.set_footer(text=f"Your current voice: {current_speaker_name}")
        else:
            _ = embed.set_footer(text="You're using the default voice")

        return embed

    except Exception:
        from loguru import logger

        logger.bind(engine=config.tts_engine, user_id=str(user_id)).exception("Error creating voices embed")
        return discord.Embed(title="🎭 Available Voices", color=discord.Color.red(), description="❌ Error retrieving voice information")
