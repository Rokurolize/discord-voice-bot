"""Voice slash command handler."""

import asyncio
from collections.abc import Mapping
from typing import Any, cast

import discord
from loguru import logger

from ...bot import DiscordVoiceTTSBot
from ...config import EngineConfig


async def handle(interaction: discord.Interaction, bot: DiscordVoiceTTSBot, speaker: str | None = None) -> None:
    """
    Handle the `/voice` slash command: view, set, reset user voice preference, and test the selected voice.

    If called with no speaker argument, sends an ephemeral embed describing the current user voice setting and available subcommands.
    If called with "reset" (case-insensitive), removes the user's custom voice preference and responds with the outcome.
    If called with a speaker name or numeric ID, looks up the configured speakers for the active TTS engine, saves the matching preference, responds with success or failure, and — on success — enqueues a short test utterance for playback.

    Args:
        interaction: Command interaction context.
        bot: The Discord bot instance handling the command.
        speaker: Optional speaker name or numeric ID to set; use "reset" to remove a custom setting. When omitted, the command displays the current setting.

    Side effects:
        - Sends ephemeral responses (or follow-up if the initial response is already sent).
        - Updates persistent user settings via the project's user settings API.
        - May add a test message to the bot's voice queue (if a voice handler is available).

    Raises:
        asyncio.CancelledError: re-raised if the coroutine is cancelled.

    """
    logger.debug(
        "Handling /voice command from user id={} name={} speaker={}",
        interaction.user.id,
        interaction.user.display_name,
        (speaker if speaker is None else (speaker[:64] + "…") if len(speaker) > 64 else speaker),
    )
    try:
        from ...user_settings import load_user_settings

        user_id = str(interaction.user.id)
        user_settings = load_user_settings()

        # If no speaker specified, show current setting
        if speaker is None:
            current_settings = user_settings.get_user_settings(user_id)
            if current_settings:
                embed = discord.Embed(
                    title="🎭 Your Voice Settings",
                    color=discord.Color.blue(),
                    description=f"Current voice: **{current_settings['speaker_name']}** (ID: {current_settings['speaker_id']})",
                )
            else:
                embed = discord.Embed(
                    title="🎭 Your Voice Settings",
                    color=discord.Color.greyple(),
                    description="No custom voice set. Using default voice.",
                )
            _ = embed.add_field(
                name="Commands",
                value="`/voice <name>` - Set voice\n`/voice reset` - Reset to default\n`/voices` - List available",
                inline=False,
            )
            _ = await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        # Handle reset
        sp = speaker.strip()
        if sp.lower() == "reset":
            if user_settings.remove_user_speaker(user_id):
                _ = await interaction.response.send_message("✅ Voice preference reset to default", ephemeral=True)
            else:
                _ = await interaction.response.send_message("ℹ️ You don't have a custom voice set", ephemeral=True)
            return

        # Get available speakers from static mapping (no engine startup needed)
        config = bot.config
        if config is None or not hasattr(config, "engines") or not hasattr(config, "tts_engine"):
            _ = await interaction.response.send_message("❌ Configuration unavailable; try again later.", ephemeral=True)
            return
        engine_key = (config.tts_engine or "voicevox").lower()
        engine_cfg = cast(EngineConfig, config.engines.get(engine_key, {}))
        speakers_map: Mapping[str, int] = engine_cfg.get("speakers", {})
        speakers: dict[str, int] = dict(speakers_map)
        if not speakers:
            _ = await interaction.response.send_message(
                f"❌ No speakers configured for engine '{engine_key}'. Use `/voices` to inspect configuration.",
                ephemeral=True,
            )
            return

        # Find matching speaker (case-insensitive)
        speaker_lower = sp.lower()
        matched_speaker: str | None = None
        matched_id: int | None = None

        for name, speaker_id in speakers.items():
            if name.lower() == speaker_lower or str(speaker_id) == sp:
                matched_speaker = name
                matched_id = speaker_id
                break

        if matched_speaker and matched_id is not None:
            # Pass current engine to ensure proper mapping
            if user_settings.set_user_speaker(user_id, matched_id, matched_speaker, config.tts_engine):
                _ = await interaction.response.send_message(f"✅ Voice set to **{matched_speaker}** (ID: {matched_id}) on {config.tts_engine.upper()}", ephemeral=True)
                # Test the new voice
                test_text = f"{matched_speaker}の声です"
                if hasattr(bot, "voice_handler") and bot.voice_handler:
                    mp: Any = getattr(bot, "message_processor", None)
                    chunks: list[str] = mp.chunk_message(test_text) if mp and hasattr(mp, "chunk_message") else [test_text]
                    processed_message = {
                        "text": test_text,
                        "user_id": interaction.user.id,
                        "username": interaction.user.display_name,
                        "chunks": chunks,
                        "group_id": f"slash_voice_test_{interaction.id}",
                    }
                    _ = await bot.voice_handler.add_to_queue(processed_message)
            else:
                _ = await interaction.response.send_message("❌ Failed to save voice preference", ephemeral=True)
        else:
            _ = await interaction.response.send_message(f"❌ Voice '{speaker}' not found. Use `/voices` to see available options.", ephemeral=True)

    except asyncio.CancelledError:
        raise
    except Exception:
        logger.exception("Error in voice slash command")
        try:
            if interaction.response.is_done():
                _ = await interaction.followup.send("❌ Error setting voice preference", ephemeral=True)
            else:
                _ = await interaction.response.send_message("❌ Error setting voice preference", ephemeral=True)
        except Exception as followup_err:
            logger.opt(exception=followup_err).debug("Suppressed secondary error while responding to interaction")
